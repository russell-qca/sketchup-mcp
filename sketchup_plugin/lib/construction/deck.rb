# frozen_string_literal: true

module Construction
  # Deck - Generate 3D deck geometry based on structural calculations
  # Handles footers, posts, beams, joists, decking, and stairs
  class Deck

    # Create a complete deck assembly
    def self.create(params)
      SU_MCP.model.start_operation('Create Deck', true)

      # Extract parameters
      length_ft = params['length'] || 12.0
      width_ft = params['width'] || 16.0
      height_in = params['height'] || 24.0
      origin = params['origin'] || [0, 0, 0]

      # Convert to inches
      length = length_ft * 12.0
      width = width_ft * 12.0
      height = height_in

      # Structural member sizes (from calculations or defaults)
      joist_size = params['joist_size'] || '2x10'
      joist_spacing = params['joist_spacing'] || 16.0
      beam_size = params['beam_size'] || '2x10'
      post_size = params['post_size'] || '4x4'
      footing_diameter = params['footing_diameter'] || 12.0

      # Parse origin point
      origin_pt = Geom::Point3d.new(origin)

      SU_MCP.log "[DECK] Creating #{length_ft}' x #{width_ft}' deck at height #{height_in}\""
      SU_MCP.log "[DECK] Joists: #{joist_size} @ #{joist_spacing}\" OC"
      SU_MCP.log "[DECK] Beams: (2) #{beam_size}"
      SU_MCP.log "[DECK] Posts: #{post_size}"

      # Create main deck group
      deck_group = SU_MCP.model.active_entities.add_group
      deck_group.name = "DECK_#{length_ft}x#{width_ft}_#{Time.now.to_i}"
      entities = deck_group.entities

      # Build deck components in order (bottom to top)
      components_created = []

      # 1. Footings (at grade level, extending down)
      footing_count = create_footings(
        entities,
        origin_pt,
        length,
        width,
        height,
        footing_diameter,
        post_size
      )
      components_created << "#{footing_count} footings"

      # 2. Posts (from footings to beam height)
      post_count = create_posts(
        entities,
        origin_pt,
        length,
        width,
        height,
        post_size
      )
      components_created << "#{post_count} posts"

      # 3. Beams (on top of posts)
      beam_count = create_beams(
        entities,
        origin_pt,
        length,
        width,
        height,
        beam_size
      )
      components_created << "#{beam_count} beams"

      # 4. Joists (perpendicular to house, resting on beams)
      joist_count = create_joists(
        entities,
        origin_pt,
        length,
        width,
        height,
        joist_size,
        joist_spacing
      )
      components_created << "#{joist_count} joists"

      # 5. Decking (on top of joists)
      board_count = create_decking(
        entities,
        origin_pt,
        length,
        width,
        height,
        joist_size
      )
      components_created << "#{board_count} deck boards"

      SU_MCP.model.commit_operation

      {
        status: 'created',
        type: 'deck',
        engine: 'custom',
        group_name: deck_group.name,
        dimensions: {
          length_ft: length_ft,
          width_ft: width_ft,
          height_in: height_in,
          area_sqft: length_ft * width_ft
        },
        components: components_created,
        message: "Created #{length_ft}' × #{width_ft}' deck (#{components_created.join(', ')})"
      }

    rescue => e
      SU_MCP.model.abort_operation
      raise "Deck creation error: #{e.message}"
    end

    private

    # Create footings at each post location
    def self.create_footings(entities, origin, length, width, height, diameter_in, post_size)
      SU_MCP.log "[DECK] Creating footings..."

      # Footing extends 32" below grade (Ohio frost line)
      footing_depth = 32.0
      footing_radius = diameter_in / 2.0

      # Post locations (4 corners for simple deck)
      # For longer decks, we'd add intermediate posts
      post_locations = get_post_locations(origin, length, width, post_size)

      post_locations.each_with_index do |post_center, i|
        # Footing is centered under post, extends down from grade
        footing_center = Geom::Point3d.new(
          post_center.x,
          post_center.y,
          origin.z - footing_depth
        )

        # Create cylinder for footing (circle extruded up)
        footing_circle = entities.add_circle(
          footing_center,
          Z_AXIS,
          footing_radius,
          24  # segments
        )

        # Find the circular face
        footing_face = nil
        entities.each { |e| footing_face = e if e.is_a?(Sketchup::Face) && !footing_face }

        if footing_face
          footing_face.pushpull(footing_depth)
        end
      end

      post_locations.length
    end

    # Create posts from footings to beam height
    def self.create_posts(entities, origin, length, width, height, post_size)
      SU_MCP.log "[DECK] Creating posts..."

      # Parse post size (e.g., "4x4" -> 3.5" x 3.5" actual)
      post_width, post_depth = parse_lumber_size(post_size)

      post_locations = get_post_locations(origin, length, width, post_size)

      post_locations.each do |post_center|
        # Post starts at grade (origin.z) and goes up to deck height
        post_origin = Geom::Point3d.new(
          post_center.x - post_width / 2,
          post_center.y - post_depth / 2,
          origin.z
        )

        # Create rectangular post
        create_lumber_piece(
          entities,
          post_origin,
          post_width,
          post_depth,
          height,
          X_AXIS  # Post oriented along X
        )
      end

      post_locations.length
    end

    # Create beams on top of posts
    def self.create_beams(entities, origin, length, width, height, beam_size)
      SU_MCP.log "[DECK] Creating beams..."

      # Parse beam size (double 2x, e.g., "2x10" -> 1.5" x 9.25" actual, doubled = 3.0" x 9.25")
      beam_width, beam_depth = parse_lumber_size(beam_size)
      beam_width = beam_width * 2  # Double 2x beam

      # Beams run parallel to house (along length direction)
      # Typically one beam at front edge, one at back edge
      beam_y_positions = [
        origin.y,          # Front beam
        origin.y + width   # Back beam
      ]

      beam_y_positions.each do |y_pos|
        beam_origin = Geom::Point3d.new(
          origin.x,
          y_pos - beam_depth / 2,
          origin.z + height
        )

        create_lumber_piece(
          entities,
          beam_origin,
          length,         # Beam spans the full length
          beam_width,     # Width (3" for double 2x)
          beam_depth,     # Depth (e.g., 9.25" for 2x10)
          X_AXIS          # Beam oriented along X (length direction)
        )
      end

      beam_y_positions.length
    end

    # Create joists spanning from front beam to back beam
    def self.create_joists(entities, origin, length, width, height, joist_size, joist_spacing)
      SU_MCP.log "[DECK] Creating joists @ #{joist_spacing}\" OC..."

      # Parse joist size
      joist_width, joist_depth = parse_lumber_size(joist_size)

      # Joists run perpendicular to house (Y direction), spaced along X
      num_joists = (length / joist_spacing).floor + 1

      joist_count = 0
      num_joists.times do |i|
        x_pos = origin.x + (i * joist_spacing)

        # Don't exceed deck length
        break if x_pos > origin.x + length

        joist_origin = Geom::Point3d.new(
          x_pos - joist_width / 2,
          origin.y,
          origin.z + height
        )

        create_lumber_piece(
          entities,
          joist_origin,
          joist_width,
          width,          # Joist spans the full width
          joist_depth,
          Y_AXIS          # Joist oriented along Y (width direction)
        )

        joist_count += 1
      end

      joist_count
    end

    # Create deck boards on top of joists
    def self.create_decking(entities, origin, length, width, height, joist_size)
      SU_MCP.log "[DECK] Creating deck boards..."

      # Typical deck board: 5/4 x 6 (actual 1" x 5.5")
      board_thickness = 1.0
      board_width = 5.5

      # Parse joist size to get height
      _, joist_depth = parse_lumber_size(joist_size)

      # Deck boards run parallel to house (X direction), spaced along Y
      # Typical 1/4" gap between boards
      board_gap = 0.25
      num_boards = (width / (board_width + board_gap)).floor

      board_count = 0
      num_boards.times do |i|
        y_pos = origin.y + (i * (board_width + board_gap))

        board_origin = Geom::Point3d.new(
          origin.x,
          y_pos,
          origin.z + height + joist_depth  # On top of joists
        )

        create_lumber_piece(
          entities,
          board_origin,
          length,           # Board spans full length
          board_width,
          board_thickness,
          X_AXIS            # Board oriented along X
        )

        board_count += 1
      end

      board_count
    end

    # Get post locations for a deck
    def self.get_post_locations(origin, length, width, post_size)
      # For simple deck: 4 corner posts
      # For larger decks, would add intermediate posts based on beam spans

      post_width, post_depth = parse_lumber_size(post_size)

      [
        Geom::Point3d.new(origin.x + post_width / 2, origin.y + post_depth / 2, origin.z),                    # Front left
        Geom::Point3d.new(origin.x + length - post_width / 2, origin.y + post_depth / 2, origin.z),           # Front right
        Geom::Point3d.new(origin.x + length - post_width / 2, origin.y + width - post_depth / 2, origin.z),   # Back right
        Geom::Point3d.new(origin.x + post_width / 2, origin.y + width - post_depth / 2, origin.z)             # Back left
      ]
    end

    # Create a rectangular lumber piece
    def self.create_lumber_piece(entities, origin, width, depth, height, orientation)
      # Create rectangular cross-section based on orientation
      if orientation == X_AXIS
        # Lumber runs along X, cross-section in YZ plane
        pts = [
          origin,
          Geom::Point3d.new(origin.x, origin.y + depth, origin.z),
          Geom::Point3d.new(origin.x, origin.y + depth, origin.z + height),
          Geom::Point3d.new(origin.x, origin.y, origin.z + height)
        ]
        extrude_distance = width
        extrude_direction = X_AXIS
      else
        # Lumber runs along Y, cross-section in XZ plane
        pts = [
          origin,
          Geom::Point3d.new(origin.x + width, origin.y, origin.z),
          Geom::Point3d.new(origin.x + width, origin.y, origin.z + height),
          Geom::Point3d.new(origin.x, origin.y, origin.z + height)
        ]
        extrude_distance = depth
        extrude_direction = Y_AXIS
      end

      # Create face and extrude
      face = entities.add_face(pts)
      face.pushpull(extrude_distance) if face

      face
    end

    # Parse lumber size string to actual dimensions
    # Examples: "2x4" -> [1.5, 3.5], "2x10" -> [1.5, 9.25], "4x4" -> [3.5, 3.5]
    def self.parse_lumber_size(size_str)
      nominal_to_actual = {
        '2' => 1.5,
        '4' => 3.5,
        '6' => 5.5,
        '8' => 7.25,
        '10' => 9.25,
        '12' => 11.25
      }

      parts = size_str.downcase.split('x')
      return [3.5, 3.5] unless parts.length == 2

      width = nominal_to_actual[parts[0]] || parts[0].to_f
      depth = nominal_to_actual[parts[1]] || parts[1].to_f

      [width, depth]
    end

  end
end
