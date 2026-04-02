# sketchup_mcp_server.rb
# SketchUp MCP Bridge Plugin
# Installs a local HTTP server inside SketchUp that the Python MCP server talks to.
#
# Installation: Copy this file into your SketchUp Plugins directory.
#   macOS: ~/Library/Application Support/SketchUp <version>/SketchUp/Plugins/
#   Windows: %APPDATA%\SketchUp\SketchUp <version>\SketchUp\Plugins\
#
# After copying, restart SketchUp. The server will auto-start on port 8080.

puts "====== LOADING SKETCHUP MCP PLUGIN ======"

require 'socket'
require 'json'
require 'sketchup'
require 'uri'
require 'cgi'
require 'thread'

puts "====== REQUIRES COMPLETE ======"

# Load construction modules
require_relative 'lib/construction'

puts "====== CONSTRUCTION MODULES LOADED ======"

module SU_MCP
  PORT = 8080

  # Constants
  ORIGIN = Geom::Point3d.new(0, 0, 0)
  X_AXIS = Geom::Vector3d.new(1, 0, 0)
  Y_AXIS = Geom::Vector3d.new(0, 1, 0)
  Z_AXIS = Geom::Vector3d.new(0, 0, 1)

  # Thread-safe request queue for main thread execution
  @request_queue = []
  @queue_mutex = Mutex.new
  @queue_cv = ConditionVariable.new
  @timer_id = nil
  @last_request_timing = {}

  # Logging to console for debugging (file logging disabled for performance)
  def self.log(message)
    timestamp = Time.now.strftime("%Y-%m-%d %H:%M:%S.%L")
    log_line = "[#{timestamp}] #{message}"
    puts log_line
  end

  # ---------------------------------------------------------------------------
  # Helpers
  # ---------------------------------------------------------------------------

  def self.model
    Sketchup.active_model
  end

  def self.entities
    model.entities
  end

  def self.send_json_response(data, status = 200)
    json = JSON.generate(data)
    status_text = status == 200 ? "OK" : (status == 404 ? "Not Found" : "Error")

    response = "HTTP/1.1 #{status} #{status_text}\r\n"
    response += "Content-Type: application/json\r\n"
    response += "Content-Length: #{json.bytesize}\r\n"
    response += "Access-Control-Allow-Origin: *\r\n"
    response += "Connection: close\r\n"
    response += "\r\n"
    response += json
    response
  end

  def self.send_error_response(message, status = 400)
    send_json_response({ error: message }, status)
  end

  # ---------------------------------------------------------------------------
  # Tool handlers — each returns a plain Ruby object (will be JSON-encoded)
  # ---------------------------------------------------------------------------

  # --- Query ---

  def self.handle_get_model_info(params = {})
    m = model
    {
      name:         m.title,
      description:  m.description,
      path:         m.path,
      modified:     m.modified?,
      unit:         m.options['UnitsOptions']['LengthUnit'],
      entity_count: m.entities.count,
      layer_count:  m.layers.count,
      material_count: m.materials.count
    }
  end

  def self.handle_list_layers(params = {})
    model.layers.map { |l| { name: l.name, visible: l.visible? } }
  end

  def self.handle_list_materials(params = {})
    model.materials.map do |mat|
      color = mat.color
      {
        name:  mat.name,
        color: { r: color.red, g: color.green, b: color.blue, a: color.alpha },
        texture: mat.texture ? mat.texture.filename : nil
      }
    end
  end

  def self.handle_list_entities(params = {})
    ents = params['group_name'] ? find_group(params['group_name'])&.entities : model.entities
    raise "Group not found: #{params['group_name']}" unless ents

    ents.map do |e|
      base = { id: e.entityID, type: e.class.name }
      case e
      when Sketchup::Group
        base.merge!(name: e.name, layer: e.layer.name)
      when Sketchup::ComponentInstance
        base.merge!(name: e.definition.name, layer: e.layer.name)
      when Sketchup::Face
        base.merge!(area: e.area, layer: e.layer.name, normal: vec3(e.normal))
      when Sketchup::Edge
        base.merge!(length: e.length, layer: e.layer.name)
      end
      base
    end
  end

  def self.handle_list_components(params = {})
    model.definitions.map do |defn|
      {
        name:        defn.name,
        description: defn.description,
        path:        defn.path,
        instance_count: defn.instances.count,
        entity_count:   defn.entities.count
      }
    end
  end

  # --- Create geometry ---

  def self.handle_create_face(params = {})
    pts = parse_points(params['points'])
    raise "Need at least 3 points" if pts.length < 3
    model.start_operation('MCP Create Face', true)
    face = entities.add_face(pts)
    apply_layer(face, params['layer'])
    apply_material(face, params['material'])
    model.commit_operation
    { id: face.entityID, type: 'Face', area: face.area, normal: vec3(face.normal) }
  end

  def self.handle_create_edge(params = {})
    pt1 = parse_point(params['start'])
    pt2 = parse_point(params['end'])
    model.start_operation('MCP Create Edge', true)
    edge = entities.add_line(pt1, pt2)
    apply_layer(edge, params['layer'])
    model.commit_operation
    { id: edge.entityID, type: 'Edge', length: edge.length }
  end

  def self.handle_create_group(params = {})
    model.start_operation('MCP Create Group', true)

    group = nil
    if params['entities']
      ids = params['entities'].map(&:to_i)
      ents_to_add = entities.select { |e| ids.include?(e.entityID) }
      raise "No matching entities found to group" if ents_to_add.empty?
      group = entities.add_group(ents_to_add)
    else
      group = entities.add_group
    end

    group.name = params['name'] || ''
    apply_layer(group, params['layer'])

    model.commit_operation
    { id: group.entityID, name: group.name }
  end

  def self.handle_create_box(params = {})
    x = params['width'].to_f
    y = params['depth'].to_f
    z = params['height'].to_f
    origin = params['origin'] ? parse_point(params['origin']) : ORIGIN

    model.start_operation('MCP Create Box', true)
    pts = [
      origin,
      origin.offset(X_AXIS, x),
      origin.offset(X_AXIS, x).offset(Y_AXIS, y),
      origin.offset(Y_AXIS, y)
    ]
    face = entities.add_face(pts)
    face.pushpull(z)
    apply_layer(face, params['layer'])
    apply_material(face, params['material'])
    model.commit_operation
    { status: 'created', width: x, depth: y, height: z }
  end

  def self.handle_create_component(params = {})
    name = params['name'] || 'MCP Component'
    model.start_operation('MCP Create Component', true)
    defn = model.definitions.add(name)
    defn.description = params['description'] || ''
    pt = params['origin'] ? parse_point(params['origin']) : ORIGIN
    transform = Geom::Transformation.new(pt)
    instance = entities.add_instance(defn, transform)
    model.commit_operation
    { definition_name: defn.name, instance_id: instance.entityID }
  end

  def self.handle_place_component(params = {})
    name = params['name'] || ''
    defn = model.definitions.find { |d| d.name == name }
    raise "Component definition not found: #{name}" unless defn
    pt = params['origin'] ? parse_point(params['origin']) : ORIGIN
    transform = Geom::Transformation.new(pt)
    model.start_operation('MCP Place Component', true)
    instance = entities.add_instance(defn, transform)
    model.commit_operation
    { instance_id: instance.entityID, definition: defn.name }
  end

  # --- Advanced geometry ---

  def self.handle_create_circle(params = {})
    center = params['center'] ? parse_point(params['center']) : ORIGIN
    normal = params['normal'] ? parse_point(params['normal']) : Z_AXIS
    radius = params['radius'].to_f
    segments = params['segments'] ? params['segments'].to_i : 24

    raise "Radius must be positive" if radius <= 0
    raise "Segments must be at least 3" if segments < 3

    model.start_operation('MCP Create Circle', true)
    circle = entities.add_circle(center, normal, radius, segments)

    # Apply layer/material to all edges
    if params['layer'] || params['material']
      circle.each do |edge|
        apply_layer(edge, params['layer'])
        apply_material(edge, params['material']) if edge.respond_to?(:material=)
      end
    end

    model.commit_operation
    {
      status: 'created',
      edge_count: circle.length,
      center: vec3(center),
      radius: radius,
      segments: segments
    }
  end

  def self.handle_create_arc(params = {})
    center = params['center'] ? parse_point(params['center']) : ORIGIN
    xaxis = params['xaxis'] ? parse_point(params['xaxis']) : X_AXIS
    normal = params['normal'] ? parse_point(params['normal']) : Z_AXIS
    radius = params['radius'].to_f
    start_angle = params['start_angle'] ? params['start_angle'].to_f : 0.0
    end_angle = params['end_angle'] ? params['end_angle'].to_f : 180.0
    segments = params['segments'] ? params['segments'].to_i : 12

    raise "Radius must be positive" if radius <= 0
    raise "Segments must be at least 2" if segments < 2

    model.start_operation('MCP Create Arc', true)
    arc = entities.add_arc(center, xaxis, normal, radius, start_angle.degrees, end_angle.degrees, segments)

    if params['layer'] || params['material']
      arc.each do |edge|
        apply_layer(edge, params['layer'])
        apply_material(edge, params['material']) if edge.respond_to?(:material=)
      end
    end

    model.commit_operation
    {
      status: 'created',
      edge_count: arc.length,
      center: vec3(center),
      radius: radius,
      start_angle: start_angle,
      end_angle: end_angle
    }
  end

  def self.handle_create_polygon(params = {})
    center = params['center'] ? parse_point(params['center']) : ORIGIN
    normal = params['normal'] ? parse_point(params['normal']) : Z_AXIS
    radius = params['radius'].to_f
    num_sides = params['num_sides'].to_i
    inscribed = params['inscribed'].nil? ? true : params['inscribed']

    raise "Radius must be positive" if radius <= 0
    raise "Polygon must have at least 3 sides" if num_sides < 3

    model.start_operation('MCP Create Polygon', true)

    # add_ngon creates edges, we want to create a face
    edges = entities.add_ngon(center, normal, radius, num_sides, inscribed)

    # Try to create a face from the edges
    face = nil
    if edges.length >= 3
      points = edges.map { |e| e.start.position }
      face = entities.add_face(points) rescue nil
    end

    if params['layer'] || params['material']
      edges.each do |edge|
        apply_layer(edge, params['layer'])
      end
      if face
        apply_layer(face, params['layer'])
        apply_material(face, params['material'])
      end
    end

    model.commit_operation
    {
      status: 'created',
      edge_count: edges.length,
      face_id: face ? face.entityID : nil,
      center: vec3(center),
      radius: radius,
      num_sides: num_sides
    }
  end

  def self.handle_push_pull(params = {})
    entity_id = params['entity_id']
    distance = params['distance'].to_f

    raise "entity_id is required" unless entity_id

    entity = find_entity_by_id(entity_id)
    raise "Entity not found: #{entity_id}" unless entity
    raise "Entity must be a Face" unless entity.is_a?(Sketchup::Face)

    model.start_operation('MCP Push Pull', true)
    result = entity.pushpull(distance)
    model.commit_operation

    {
      status: 'completed',
      entity_id: entity_id,
      distance: distance,
      result_valid: !result.nil?
    }
  end

  def self.handle_follow_me(params = {})
    face_id = params['face_id']
    path_ids = params['path_ids']

    raise "face_id is required" unless face_id
    raise "path_ids array is required" unless path_ids && path_ids.is_a?(Array)

    face = find_entity_by_id(face_id)
    raise "Face not found: #{face_id}" unless face
    raise "Entity must be a Face" unless face.is_a?(Sketchup::Face)

    path_edges = path_ids.map do |id|
      edge = find_entity_by_id(id)
      raise "Edge not found: #{id}" unless edge
      raise "Entity #{id} must be an Edge" unless edge.is_a?(Sketchup::Edge)
      edge
    end

    model.start_operation('MCP Follow Me', true)
    face.followme(path_edges)
    model.commit_operation

    {
      status: 'completed',
      face_id: face_id,
      path_edge_count: path_edges.length
    }
  end

  # --- Transformations ---

  def self.handle_move_entity(params = {})
    entity_id = params['entity_id']
    vector = params['vector']

    raise "entity_id is required" unless entity_id
    raise "vector [x, y, z] is required" unless vector && vector.is_a?(Array) && vector.length == 3

    entity = find_entity_by_id(entity_id)
    raise "Entity not found: #{entity_id}" unless entity
    raise "Entity cannot be transformed" unless entity.respond_to?(:transform!)

    vec = Geom::Vector3d.new(vector[0].to_f, vector[1].to_f, vector[2].to_f)
    transform = Geom::Transformation.translation(vec)

    model.start_operation('MCP Move Entity', true)
    entity.transform!(transform)
    model.commit_operation

    {
      status: 'moved',
      entity_id: entity_id,
      vector: vec3(vec)
    }
  end

  def self.handle_rotate_entity(params = {})
    entity_id = params['entity_id']
    axis_point = params['axis_point']
    axis_vector = params['axis_vector']
    angle = params['angle'].to_f

    raise "entity_id is required" unless entity_id
    raise "axis_point [x, y, z] is required" unless axis_point
    raise "axis_vector [x, y, z] is required" unless axis_vector

    entity = find_entity_by_id(entity_id)
    raise "Entity not found: #{entity_id}" unless entity
    raise "Entity cannot be transformed" unless entity.respond_to?(:transform!)

    point = parse_point(axis_point)
    vector = Geom::Vector3d.new(axis_vector[0].to_f, axis_vector[1].to_f, axis_vector[2].to_f)
    transform = Geom::Transformation.rotation(point, vector, angle.degrees)

    model.start_operation('MCP Rotate Entity', true)
    entity.transform!(transform)
    model.commit_operation

    {
      status: 'rotated',
      entity_id: entity_id,
      angle_degrees: angle
    }
  end

  def self.handle_scale_entity(params = {})
    entity_id = params['entity_id']
    scale = params['scale']
    origin = params['origin'] ? parse_point(params['origin']) : ORIGIN

    raise "entity_id is required" unless entity_id

    entity = find_entity_by_id(entity_id)
    raise "Entity not found: #{entity_id}" unless entity
    raise "Entity cannot be transformed" unless entity.respond_to?(:transform!)

    transform = nil
    if scale.is_a?(Array) && scale.length == 3
      # Non-uniform scaling
      transform = Geom::Transformation.scaling(origin, scale[0].to_f, scale[1].to_f, scale[2].to_f)
      scale_info = { x: scale[0].to_f, y: scale[1].to_f, z: scale[2].to_f }
    else
      # Uniform scaling
      s = scale.to_f
      transform = Geom::Transformation.scaling(origin, s, s, s)
      scale_info = { uniform: s }
    end

    model.start_operation('MCP Scale Entity', true)
    entity.transform!(transform)
    model.commit_operation

    {
      status: 'scaled',
      entity_id: entity_id,
      scale: scale_info
    }
  end

  # --- Execute arbitrary Ruby ---

  def self.handle_execute_ruby(params = {})
    code = params['code'] || ''
    raise "No code provided" if code.strip.empty?

    result = nil
    output = []

    # Capture puts/print output
    old_stdout = $stdout
    $stdout = StringIO.new

    begin
      result = eval(code, binding) # rubocop:disable Security/Eval
      output = $stdout.string.split("\n")
    ensure
      $stdout = old_stdout
    end

    {
      result: result.inspect,
      output: output
    }
  rescue => e
    { error: e.message, backtrace: e.backtrace.first(5) }
  end

  # ---------------------------------------------------------------------------
  # Internal helpers
  # ---------------------------------------------------------------------------

  def self.parse_point(arr)
    Geom::Point3d.new(arr[0].to_f, arr[1].to_f, arr[2].to_f)
  end

  def self.parse_points(arr)
    arr.map { |p| parse_point(p) }
  end

  def self.vec3(v)
    { x: v.x, y: v.y, z: v.z }
  end

  def self.find_group(name)
    entities.find { |e| e.is_a?(Sketchup::Group) && e.name == name }
  end

  def self.find_entity_by_id(entity_id)
    id = entity_id.to_i
    entities.find { |e| e.entityID == id }
  end

  def self.apply_layer(entity, layer_name)
    return unless layer_name
    layer = model.layers[layer_name] || model.layers.add(layer_name)
    entity.layer = layer
  end

  def self.apply_material(entity, mat_name)
    return unless mat_name
    mat = model.materials[mat_name] || model.materials.add(mat_name)
    entity.material = mat if entity.respond_to?(:material=)
  end

  # ---------------------------------------------------------------------------
  # Construction - Delegated to separate modules in lib/construction/
  # ---------------------------------------------------------------------------

  # Old truss helper methods have been moved to Construction::RoofTruss module


  # Main roof truss handler - uses Medeek if available, falls back to built-in
  def self.handle_create_roof_truss(params = {})
    if Construction::MedeekTruss.available?
      begin
        result = Construction::MedeekTruss.create(params)
        # If Medeek succeeded, return its result
        if result && result[:status] == 'created'
          return result
        else
          # Medeek failed to create trusses
          error_msg = "Medeek Truss Plugin failed to create trusses. This may be due to invalid parameters or license issues. Using built-in implementation as fallback."
          log "[SU_MCP] #{error_msg}"
          built_in_result = Construction::RoofTruss.create(params)
          built_in_result[:warning] = error_msg
          built_in_result[:engine] = 'built-in (medeek failed)'
          return built_in_result
        end
      rescue => e
        error_msg = "Medeek Truss Plugin error: #{e.message}. Using built-in implementation as fallback."
        log "[SU_MCP] #{error_msg}"
        built_in_result = Construction::RoofTruss.create(params)
        built_in_result[:warning] = error_msg
        built_in_result[:engine] = 'built-in (medeek error)'
        return built_in_result
      end
    else
      # Medeek not installed
      log "[SU_MCP] Medeek Truss Plugin not detected, using built-in implementation"
      built_in_result = Construction::RoofTruss.create(params)
      built_in_result[:info] = "Using built-in truss implementation. Install Medeek Truss Plugin for professional-grade trusses with more types and features."
      built_in_result[:engine] = 'built-in (medeek not installed)'
      return built_in_result
    end
  end

  # Wall handler - delegates to Construction::Wall module
  def self.handle_create_wall(params = {})
    Construction::Wall.create(params)
  end

  # ---------------------------------------------------------------------------
  # HTTP Server (using TCPServer instead of WEBrick for Ruby 3.2+)
  # ---------------------------------------------------------------------------

  ROUTES = {
    # GET
    ['GET',  '/model/info']        => :handle_get_model_info,
    ['GET',  '/model/layers']      => :handle_list_layers,
    ['GET',  '/model/materials']   => :handle_list_materials,
    ['GET',  '/model/entities']    => :handle_list_entities,
    ['GET',  '/model/components']  => :handle_list_components,
    # POST - Basic geometry
    ['POST', '/geometry/face']     => :handle_create_face,
    ['POST', '/geometry/edge']     => :handle_create_edge,
    ['POST', '/geometry/group']    => :handle_create_group,
    ['POST', '/geometry/box']      => :handle_create_box,
    # POST - Advanced geometry
    ['POST', '/geometry/circle']   => :handle_create_circle,
    ['POST', '/geometry/arc']      => :handle_create_arc,
    ['POST', '/geometry/polygon']  => :handle_create_polygon,
    ['POST', '/geometry/pushpull'] => :handle_push_pull,
    ['POST', '/geometry/followme'] => :handle_follow_me,
    # POST - Transformations
    ['POST', '/transform/move']    => :handle_move_entity,
    ['POST', '/transform/rotate']  => :handle_rotate_entity,
    ['POST', '/transform/scale']   => :handle_scale_entity,
    # POST - Components
    ['POST', '/components/create'] => :handle_create_component,
    ['POST', '/components/place']  => :handle_place_component,
    # POST - Construction
    ['POST', '/construction/roof_truss'] => :handle_create_roof_truss,
    ['POST', '/construction/wall']       => :handle_create_wall,
    # POST - Ruby
    ['POST', '/ruby/execute']      => :handle_execute_ruby,
  }

  def self.parse_http_request(request_text)
    lines = request_text.split("\r\n")
    request_line = lines[0]
    method, path, _ = request_line.split(' ')

    # Parse path and query string
    uri = URI.parse(path)
    query_params = uri.query ? CGI.parse(uri.query) : {}

    # Find body (after blank line)
    body_index = lines.index('')
    body = body_index ? lines[(body_index + 1)..-1].join("\r\n") : ''

    { method: method, path: uri.path, query: query_params, body: body }
  end

  def self.handle_request(request)
    log "[SU_MCP] ===== Received HTTP request ====="

    req = parse_http_request(request)
    method = req[:method]
    path = req[:path]

    log "[SU_MCP] Parsed: #{method} #{path}"

    handler = ROUTES[[method, path]]

    unless handler
      log "[SU_MCP] Unknown route: #{method} #{path}"
      return send_error_response("Unknown route: #{method} #{path}", 404)
    end

    log "[SU_MCP] Handler: #{handler}"

    # Parse parameters
    params = {}
    if method == 'POST' && !req[:body].empty?
      begin
        params = JSON.parse(req[:body])
      rescue JSON::ParserError => e
        return send_error_response("Invalid JSON: #{e.message}", 400)
      end
    elsif method == 'GET'
      req[:query].each { |k, v| params[k] = v.first }
    end

    # Create request object for main thread execution
    request_obj = {
      handler: handler,
      params: params,
      response: nil,
      error: nil,
      completed: false
    }

    log "[SU_MCP] Enqueueing request: #{method} #{path}"

    # Enqueue request for main thread processing
    @queue_mutex.synchronize do
      @request_queue << request_obj
      @queue_cv.signal
      log "[SU_MCP] Queue size: #{@request_queue.length}"
    end

    # Wait for completion with simple polling (no condition variable)
    timeout_at = Time.now + 30
    until request_obj[:completed]
      if Time.now > timeout_at
        return send_error_response("Request timeout", 504)
      end
      sleep(0.001)  # 1ms sleep between checks
    end

    # Return response or error
    if request_obj[:error]
      send_error_response("#{request_obj[:error][:class]}: #{request_obj[:error][:message]}", 500)
    else
      send_json_response(request_obj[:response])
    end

  rescue => e
    send_error_response("#{e.class}: #{e.message}", 500)
  end

  # Process queued requests on the main thread
  def self.process_queue
    # Get request without holding mutex during execution
    request_obj = nil
    @queue_mutex.synchronize do
      return if @request_queue.empty?
      request_obj = @request_queue.shift
    end

    return unless request_obj

    log "[SU_MCP] Processing handler: #{request_obj[:handler]}"

    begin
      # Execute handler on main thread WITHOUT holding mutex
      # This prevents deadlocks and allows HTTP thread to check status
      result = public_send(request_obj[:handler], request_obj[:params])

      # Update result (no mutex needed for simple assignment)
      request_obj[:response] = result
      request_obj[:completed] = true

      log "[SU_MCP] Handler completed successfully"
    rescue => e
      log "[SU_MCP] Handler error: #{e.class}: #{e.message}"
      log e.backtrace.first(5).join("\n")

      # Update error (no mutex needed for simple assignment)
      request_obj[:error] = { class: e.class.name, message: e.message }
      request_obj[:completed] = true
    end
  rescue => e
    log "[SU_MCP] CRITICAL ERROR in process_queue: #{e.class}: #{e.message}"
    log e.backtrace.first(10).join("\n")
  end

  # Start/stop server
  def self.start_server
    return if @server

    begin
      @server = TCPServer.new('127.0.0.1', PORT)
      @running = true

      @thread = Thread.new do
        begin
          while @running
            begin
              client = @server.accept
              request = ''
              start_time = Time.now

              # Read request
              while (line = client.gets) && line !~ /^\s*$/
                request += line
              end
              read_time = Time.now

              # Read body if present
              if request =~ /Content-Length: (\d+)/i
                content_length = $1.to_i
                request += "\r\n" + client.read(content_length)
              end

              # Store timing
              @last_request_timing = {
                accept_to_read: ((read_time - start_time) * 1000).round(1),
                request_size: request.length,
                handle_start: Time.now
              }

              # Handle request
              response = handle_request(request)
              handle_time = Time.now

              @last_request_timing[:handle_duration] = ((handle_time - @last_request_timing[:handle_start]) * 1000).round(1)

              client.write(response)
              write_time = Time.now

              @last_request_timing[:write_duration] = ((write_time - handle_time) * 1000).round(1)
              @last_request_timing[:total] = ((write_time - start_time) * 1000).round(1)

              # Schedule main thread to log this
              UI.start_timer(0) do
                log "[SU_MCP] Request timing: read=#{@last_request_timing[:accept_to_read]}ms, handle=#{@last_request_timing[:handle_duration]}ms, write=#{@last_request_timing[:write_duration]}ms, TOTAL=#{@last_request_timing[:total]}ms"
              end

            rescue => e
              UI.start_timer(0) { log "[SU_MCP] Request error: #{e.message}" }
            ensure
              client.close if client
            end
          end
        rescue => e
          UI.start_timer(0) { log "[SU_MCP] Server error: #{e.message}" }
        end
      end

      # Start main thread timer to process queued requests
      # Timer runs every 0.03 seconds (30ms) to check for pending requests
      @timer_id = UI.start_timer(0.03, true) { SU_MCP.process_queue }
      log "[SU_MCP] Main thread timer started (ID: #{@timer_id})"

      UI.messagebox("SketchUp MCP Server started on port #{PORT}") if defined?(UI)
      log "[SU_MCP] Server running on http://localhost:#{PORT}"
      log "[SU_MCP] Logging to Ruby Console (Window → Ruby Console)"

    rescue Errno::EADDRINUSE
      error_msg = "Port #{PORT} is already in use. Another instance may be running.\n\n" \
                  "Try:\n" \
                  "1. Close other SketchUp windows\n" \
                  "2. Use 'lsof -i :#{PORT}' to find the process\n" \
                  "3. Change PORT in the plugin file if needed"

      puts "[SU_MCP] ERROR: #{error_msg}"
      UI.messagebox(error_msg, MB_OK) if defined?(UI)

      @server = nil
      @thread = nil
    rescue => e
      error_msg = "Failed to start server: #{e.class} - #{e.message}"
      puts "[SU_MCP] ERROR: #{error_msg}"
      UI.messagebox(error_msg, MB_OK) if defined?(UI)

      @server = nil
      @thread = nil
    end
  end

  def self.stop_server
    return unless @server

    @running = false

    # Stop the main thread timer
    UI.stop_timer(@timer_id) if @timer_id
    @timer_id = nil

    @server.close
    @thread&.join(2)
    @server = nil
    @thread = nil

    puts "[SU_MCP] Server stopped"
  end

  def self.restart_server
    stop_server
    start_server
  end

  # ---------------------------------------------------------------------------
  # SketchUp plugin registration
  # ---------------------------------------------------------------------------
  unless file_loaded?(__FILE__)
    log "[SU_MCP] ===== Plugin loading ====="
    log "[SU_MCP] Ruby version: #{RUBY_VERSION}"
    log "[SU_MCP] SketchUp version: #{Sketchup.version}"

    # Add menu items
    menu = UI.menu('Plugins').add_submenu('MCP Server')
    menu.add_item('Start Server')   { SU_MCP.start_server }
    menu.add_item('Stop Server')    { SU_MCP.stop_server }
    menu.add_item('Restart Server') { SU_MCP.restart_server }

    log "[SU_MCP] Menu items added"

    # Auto-start when SketchUp loads
    SU_MCP.start_server

    file_loaded(__FILE__)
    log "[SU_MCP] Plugin loaded successfully"
  end
end
