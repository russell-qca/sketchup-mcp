# frozen_string_literal: true

module Construction
  # MedeekWall - Wrapper for Medeek Wall Plugin API
  # Provides methods for creating and manipulating wall assemblies using the Medeek Wall Plugin
  module MedeekWall

    # Check if Medeek Wall Plugin is available
    def self.available?
      begin
        defined?(Medeek_Engineering_Inc_Extensions::MedeekWallPlugin::Wall::MedeekMethods)
      rescue
        false
      end
    end

    # Get the Medeek Wall Plugin module (deferred constant lookup)
    def self.get_medeek_module
      return nil unless available?
      Medeek_Engineering_Inc_Extensions::MedeekWallPlugin::Wall::MedeekMethods
    end

    # ──────────────────────────────────────────────────────────────────────
    # WALL CREATION METHODS
    # ──────────────────────────────────────────────────────────────────────

    # Create a single wall between two points
    def self.create_wall(params)
      SU_MCP.model.start_operation('Create Wall', true)

      # Extract parameters
      start_point = params['start_point']
      end_point = params['end_point']
      wall_family = params['wall_family'] || 'Rectangular'
      wall_type = params['wall_type'] || 'Int-Ext'

      # Validate required parameters
      raise "start_point is required" unless start_point
      raise "end_point is required" unless end_point

      # Validate wall_family
      valid_families = ['Rectangular', 'Gable', 'Shed', 'Hip']
      unless valid_families.include?(wall_family)
        raise "Invalid wall_family '#{wall_family}'. Must be one of: #{valid_families.join(', ')}"
      end

      # Validate wall_type
      valid_types = ['Int-Ext', 'Int-Int']
      unless valid_types.include?(wall_type)
        raise "Invalid wall_type '#{wall_type}'. Must be one of: #{valid_types.join(', ')}"
      end

      # Convert points to Geom::Point3d
      pt0 = Geom::Point3d.new(start_point)
      pt1 = Geom::Point3d.new(end_point)

      SU_MCP.log "[SU_MCP] Creating wall from #{pt0} to #{pt1}"
      SU_MCP.log "[SU_MCP] Wall family: #{wall_family}, type: #{wall_type}"

      # Get Medeek Wall Plugin module
      medeek = get_medeek_module
      raise "Medeek Wall Plugin not available. Please install and license the plugin." unless medeek

      # Create wall
      wall_result = medeek.wall_draw(pt0, pt1, wall_family, wall_type)

      raise "Failed to create wall" unless wall_result

      SU_MCP.model.commit_operation

      # Handle result - could be a single group or an array of groups
      if wall_result.is_a?(Array)
        group_names = wall_result.map { |g| g.name rescue 'unnamed' }.join(', ')
        group_count = wall_result.length
        {
          status: 'created',
          engine: 'medeek_wall',
          group_names: group_names,
          group_count: group_count,
          wall_family: wall_family,
          wall_type: wall_type,
          length: pt0.distance(pt1).to_f,
          message: "Created #{wall_family} wall with #{group_count} assemblies (#{group_names})"
        }
      else
        {
          status: 'created',
          engine: 'medeek_wall',
          group_name: wall_result.name,
          wall_family: wall_family,
          wall_type: wall_type,
          length: pt0.distance(pt1).to_f,
          message: "Created #{wall_family} wall '#{wall_result.name}'"
        }
      end

    rescue => e
      SU_MCP.model.abort_operation

      if e.message.include?("license") || e.message.include?("License")
        raise "Medeek Wall Plugin license required. Please activate your license in SketchUp."
      else
        raise "Medeek Wall Plugin error: #{e.message}"
      end
    end

    # Create wall perimeter from polygon points
    def self.create_wall_perimeter(params)
      SU_MCP.model.start_operation('Create Wall Perimeter', true)

      # Extract parameters
      outline_points = params['outline_points']
      wall_family = params['wall_family'] || 'Rectangular'
      wall_type = params['wall_type'] || 'Int-Ext'

      # Validate required parameters
      raise "outline_points is required" unless outline_points
      raise "outline_points must be an array" unless outline_points.is_a?(Array)
      raise "outline_points must have at least 3 points" if outline_points.length < 3

      # Validate wall_family
      valid_families = ['Rectangular', 'Gable', 'Shed', 'Hip']
      unless valid_families.include?(wall_family)
        raise "Invalid wall_family '#{wall_family}'. Must be one of: #{valid_families.join(', ')}"
      end

      # Validate wall_type
      valid_types = ['Int-Ext', 'Int-Int']
      unless valid_types.include?(wall_type)
        raise "Invalid wall_type '#{wall_type}'. Must be one of: #{valid_types.join(', ')}"
      end

      # Convert points
      pts = outline_points.map { |pt| Geom::Point3d.new(pt) }

      SU_MCP.log "[SU_MCP] Creating wall perimeter with #{pts.length} points"
      SU_MCP.log "[SU_MCP] Wall family: #{wall_family}, type: #{wall_type}"

      # Get Medeek Wall Plugin module
      medeek = get_medeek_module
      raise "Medeek Wall Plugin not available. Please install and license the plugin." unless medeek

      # Create perimeter walls
      medeek.wall_draw_perim(pts, wall_family, wall_type)

      SU_MCP.model.commit_operation

      {
        status: 'created',
        engine: 'medeek_wall',
        wall_family: wall_family,
        wall_type: wall_type,
        point_count: pts.length,
        message: "Created #{wall_family} wall perimeter with #{pts.length} walls"
      }

    rescue => e
      SU_MCP.model.abort_operation

      if e.message.include?("license") || e.message.include?("License")
        raise "Medeek Wall Plugin license required. Please activate your license in SketchUp."
      else
        raise "Medeek Wall Plugin error: #{e.message}"
      end
    end

    # Read all attributes from a wall assembly
    def self.read_wall_attributes(params)
      group_name = params['group_name']

      medeek = get_medeek_module
      raise "Medeek Wall Plugin not available. Please install and license the plugin." unless medeek

      if group_name
        # Find group by name
        wall_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name == group_name }
        raise "Wall group '#{group_name}' not found" unless wall_group

        attributes = medeek.wall_read_attributes(wall_group)
      else
        # Use selection
        attributes = medeek.wall_read_attributes
      end

      raise "Failed to read wall attributes" unless attributes

      {
        status: 'success',
        group_name: group_name,
        attributes: attributes
      }

    rescue => e
      if e.message.include?("license") || e.message.include?("License")
        raise "Medeek Wall Plugin license required. Please activate your license in SketchUp."
      else
        raise "Medeek Wall Plugin error: #{e.message}"
      end
    end

    # Read a single attribute from a wall assembly
    def self.read_wall_attribute(params)
      attribute_name = params['attribute_name']
      group_name = params['group_name']

      raise "attribute_name is required" unless attribute_name

      medeek = get_medeek_module
      raise "Medeek Wall Plugin not available. Please install and license the plugin." unless medeek

      if group_name
        # Find group by name
        wall_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name == group_name }
        raise "Wall group '#{group_name}' not found" unless wall_group

        value = medeek.wall_read_attribute(attribute_name, wall_group)
      else
        # Use selection
        value = medeek.wall_read_attribute(attribute_name)
      end

      {
        status: 'success',
        attribute_name: attribute_name,
        value: value
      }

    rescue => e
      if e.message.include?("license") || e.message.include?("License")
        raise "Medeek Wall Plugin license required. Please activate your license in SketchUp."
      else
        raise "Medeek Wall Plugin error: #{e.message}"
      end
    end

    # Modify a wall assembly attribute
    def self.modify_wall_attribute(params)
      group_name = params['group_name']
      attribute_name = params['attribute_name']
      value = params['value']
      regenerate = params['regenerate'].nil? ? true : params['regenerate']

      raise "attribute_name is required" unless attribute_name
      raise "value is required" if value.nil?

      SU_MCP.model.start_operation('Modify Wall Attribute', true)

      medeek = get_medeek_module
      raise "Medeek Wall Plugin not available. Please install and license the plugin." unless medeek

      if group_name
        # Find group by name
        wall_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name == group_name }
        raise "Wall group '#{group_name}' not found" unless wall_group

        result = medeek.wall_set_attribute(attribute_name, value, wall_group, regenerate)
      else
        # Use selection
        result = medeek.wall_set_attribute(attribute_name, value, regenerate)
      end

      raise "Failed to set wall attribute" unless result

      SU_MCP.model.commit_operation

      {
        status: 'modified',
        attribute_name: attribute_name,
        value: value,
        regenerated: regenerate
      }

    rescue => e
      SU_MCP.model.abort_operation

      if e.message.include?("license") || e.message.include?("License")
        raise "Medeek Wall Plugin license required. Please activate your license in SketchUp."
      else
        raise "Medeek Wall Plugin error: #{e.message}"
      end
    end

    # Add a window to a wall assembly
    def self.add_window(params)
      location = params['location']
      width = params['width']
      height = params['height']
      geometry = params['geometry'] || 'Rectangle'
      group_name = params['group_name']
      install_window = params['install_window'].nil? ? true : params['install_window']
      exterior_trim = params['exterior_trim'].nil? ? true : params['exterior_trim']
      interior_casing = params['interior_casing'].nil? ? true : params['interior_casing']

      # Validate required parameters
      raise "location is required" unless location
      raise "width is required" unless width
      raise "height is required" unless height

      # Validate geometry
      valid_geometries = ['Rectangle', 'Half Round', 'Arch', 'Gothic Arch', 'Oval', 'Octagon', 'Hexagon', 'Trapezoid', 'Pentagon']
      unless valid_geometries.include?(geometry)
        raise "Invalid geometry '#{geometry}'. Must be one of: #{valid_geometries.join(', ')}"
      end

      SU_MCP.model.start_operation('Add Window', true)

      medeek = get_medeek_module
      raise "Medeek Wall Plugin not available. Please install and license the plugin." unless medeek

      # Convert boolean to YES/NO
      install = install_window ? 'YES' : 'NO'
      trim = exterior_trim ? 'YES' : 'NO'
      casing = interior_casing ? 'YES' : 'NO'

      if group_name
        # Find group by name
        wall_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name == group_name }
        raise "Wall group '#{group_name}' not found" unless wall_group

        medeek.wall_win_draw(location.to_f, width.to_f, height.to_f, geometry, wall_group, install, trim, casing)
      else
        # Use selection
        medeek.wall_win_draw(location.to_f, width.to_f, height.to_f, geometry, nil, install, trim, casing)
      end

      SU_MCP.model.commit_operation

      {
        status: 'created',
        type: 'window',
        location: location,
        width: width,
        height: height,
        geometry: geometry,
        message: "Added #{geometry} window at #{location}\" along wall"
      }

    rescue => e
      SU_MCP.model.abort_operation

      if e.message.include?("license") || e.message.include?("License")
        raise "Medeek Wall Plugin license required. Please activate your license in SketchUp."
      else
        raise "Medeek Wall Plugin error: #{e.message}"
      end
    end

    # Read window attributes
    def self.read_window_attributes(params)
      window_name = params['window_name']
      group_name = params['group_name']

      raise "window_name is required" unless window_name

      medeek = get_medeek_module
      raise "Medeek Wall Plugin not available. Please install and license the plugin." unless medeek

      if group_name
        # Find group by name
        wall_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name == group_name }
        raise "Wall group '#{group_name}' not found" unless wall_group

        attributes = medeek.wall_win_read_attributes(window_name, wall_group)
      else
        # Use selection
        attributes = medeek.wall_win_read_attributes(window_name)
      end

      raise "Failed to read window attributes" unless attributes

      {
        status: 'success',
        window_name: window_name,
        attributes: attributes
      }

    rescue => e
      if e.message.include?("license") || e.message.include?("License")
        raise "Medeek Wall Plugin license required. Please activate your license in SketchUp."
      else
        raise "Medeek Wall Plugin error: #{e.message}"
      end
    end

    # Add a door to a wall assembly
    def self.add_door(params)
      location = params['location']
      width = params['width']
      height = params['height']
      geometry = params['geometry'] || 'Rectangle'
      group_name = params['group_name']
      install_door = params['install_door'].nil? ? true : params['install_door']
      exterior_trim = params['exterior_trim'].nil? ? true : params['exterior_trim']
      interior_casing = params['interior_casing'].nil? ? true : params['interior_casing']

      # Validate required parameters
      raise "location is required" unless location
      raise "width is required" unless width
      raise "height is required" unless height

      # Validate geometry
      valid_geometries = ['Rectangle', 'Arch']
      unless valid_geometries.include?(geometry)
        raise "Invalid geometry '#{geometry}'. Must be one of: #{valid_geometries.join(', ')}"
      end

      SU_MCP.model.start_operation('Add Door', true)

      medeek = get_medeek_module
      raise "Medeek Wall Plugin not available. Please install and license the plugin." unless medeek

      # Convert boolean to YES/NO
      install = install_door ? 'YES' : 'NO'
      trim = exterior_trim ? 'YES' : 'NO'
      casing = interior_casing ? 'YES' : 'NO'

      if group_name
        # Find group by name
        wall_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name == group_name }
        raise "Wall group '#{group_name}' not found" unless wall_group

        medeek.wall_door_draw(location.to_f, width.to_f, height.to_f, geometry, wall_group, install, trim, casing)
      else
        # Use selection
        medeek.wall_door_draw(location.to_f, width.to_f, height.to_f, geometry, nil, install, trim, casing)
      end

      SU_MCP.model.commit_operation

      {
        status: 'created',
        type: 'door',
        location: location,
        width: width,
        height: height,
        geometry: geometry,
        message: "Added #{geometry} door at #{location}\" along wall"
      }

    rescue => e
      SU_MCP.model.abort_operation

      if e.message.include?("license") || e.message.include?("License")
        raise "Medeek Wall Plugin license required. Please activate your license in SketchUp."
      else
        raise "Medeek Wall Plugin error: #{e.message}"
      end
    end

    # Read door attributes
    def self.read_door_attributes(params)
      door_name = params['door_name']
      group_name = params['group_name']

      raise "door_name is required" unless door_name

      medeek = get_medeek_module
      raise "Medeek Wall Plugin not available. Please install and license the plugin." unless medeek

      if group_name
        # Find group by name
        wall_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name == group_name }
        raise "Wall group '#{group_name}' not found" unless wall_group

        attributes = medeek.wall_door_read_attributes(door_name, wall_group)
      else
        # Use selection
        attributes = medeek.wall_door_read_attributes(door_name)
      end

      raise "Failed to read door attributes" unless attributes

      {
        status: 'success',
        door_name: door_name,
        attributes: attributes
      }

    rescue => e
      if e.message.include?("license") || e.message.include?("License")
        raise "Medeek Wall Plugin license required. Please activate your license in SketchUp."
      else
        raise "Medeek Wall Plugin error: #{e.message}"
      end
    end

    # Add a garage door to a wall assembly
    def self.add_garage_door(params)
      location = params['location']
      width = params['width']
      height = params['height']
      geometry = params['geometry'] || 'Rectangle'
      group_name = params['group_name']
      install_door = params['install_door'].nil? ? true : params['install_door']
      exterior_trim = params['exterior_trim'].nil? ? true : params['exterior_trim']
      interior_casing = params['interior_casing'].nil? ? true : params['interior_casing']

      # Validate required parameters
      raise "location is required" unless location
      raise "width is required" unless width
      raise "height is required" unless height

      # Validate geometry
      valid_geometries = ['Rectangle', 'Arch', 'Dutch']
      unless valid_geometries.include?(geometry)
        raise "Invalid geometry '#{geometry}'. Must be one of: #{valid_geometries.join(', ')}"
      end

      SU_MCP.model.start_operation('Add Garage Door', true)

      medeek = get_medeek_module
      raise "Medeek Wall Plugin not available. Please install and license the plugin." unless medeek

      # Convert boolean to YES/NO
      install = install_door ? 'YES' : 'NO'
      trim = exterior_trim ? 'YES' : 'NO'
      casing = interior_casing ? 'YES' : 'NO'

      if group_name
        # Find group by name
        wall_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name == group_name }
        raise "Wall group '#{group_name}' not found" unless wall_group

        medeek.wall_garage_draw(location.to_f, width.to_f, height.to_f, geometry, wall_group, install, trim, casing)
      else
        # Use selection
        medeek.wall_garage_draw(location.to_f, width.to_f, height.to_f, geometry, nil, install, trim, casing)
      end

      SU_MCP.model.commit_operation

      {
        status: 'created',
        type: 'garage_door',
        location: location,
        width: width,
        height: height,
        geometry: geometry,
        message: "Added #{geometry} garage door at #{location}\" along wall"
      }

    rescue => e
      SU_MCP.model.abort_operation

      if e.message.include?("license") || e.message.include?("License")
        raise "Medeek Wall Plugin license required. Please activate your license in SketchUp."
      else
        raise "Medeek Wall Plugin error: #{e.message}"
      end
    end

    # Read garage door attributes
    def self.read_garage_attributes(params)
      garage_name = params['garage_name']
      group_name = params['group_name']

      raise "garage_name is required" unless garage_name

      medeek = get_medeek_module
      raise "Medeek Wall Plugin not available. Please install and license the plugin." unless medeek

      if group_name
        # Find group by name
        wall_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name == group_name }
        raise "Wall group '#{group_name}' not found" unless wall_group

        attributes = medeek.wall_garage_read_attributes(garage_name, wall_group)
      else
        # Use selection
        attributes = medeek.wall_garage_read_attributes(garage_name)
      end

      raise "Failed to read garage door attributes" unless attributes

      {
        status: 'success',
        garage_name: garage_name,
        attributes: attributes
      }

    rescue => e
      if e.message.include?("license") || e.message.include?("License")
        raise "Medeek Wall Plugin license required. Please activate your license in SketchUp."
      else
        raise "Medeek Wall Plugin error: #{e.message}"
      end
    end

    # Add a column to a wall assembly
    def self.add_column(params)
      location = params['location']
      column_type = params['column_type'] || 'TMB'
      column_size = params['column_size'] || '6X6'
      column_height = params['column_height'] || 'FULL'
      column_ply = params['column_ply'] || 1
      column_rotation = params['column_rotation'] || 0
      group_name = params['group_name']

      # Validate required parameters
      raise "location is required" unless location

      # Validate column_type
      valid_types = ['SL', 'GLU', 'SCL', 'TMB', 'STL', 'CUSTOM', 'BLANK']
      unless valid_types.include?(column_type)
        raise "Invalid column_type '#{column_type}'. Must be one of: #{valid_types.join(', ')}"
      end

      # Validate column_ply
      valid_plies = [1, 2, 3, 4]
      unless valid_plies.include?(column_ply)
        raise "Invalid column_ply #{column_ply}. Must be one of: #{valid_plies.join(', ')}"
      end

      # Validate column_rotation
      valid_rotations = [0, 90]
      unless valid_rotations.include?(column_rotation)
        raise "Invalid column_rotation #{column_rotation}. Must be 0 or 90"
      end

      SU_MCP.model.start_operation('Add Column', true)

      medeek = get_medeek_module
      raise "Medeek Wall Plugin not available. Please install and license the plugin." unless medeek

      if group_name
        # Find group by name
        wall_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name == group_name }
        raise "Wall group '#{group_name}' not found" unless wall_group

        medeek.wall_column_draw(location.to_f, column_type, column_size, column_height, column_ply, column_rotation, wall_group)
      else
        # Use selection
        medeek.wall_column_draw(location.to_f, column_type, column_size, column_height, column_ply, column_rotation)
      end

      SU_MCP.model.commit_operation

      {
        status: 'created',
        type: 'column',
        location: location,
        column_type: column_type,
        column_size: column_size,
        column_height: column_height,
        column_ply: column_ply,
        column_rotation: column_rotation,
        message: "Added #{column_size} #{column_type} column at #{location}\" along wall"
      }

    rescue => e
      SU_MCP.model.abort_operation

      if e.message.include?("license") || e.message.include?("License")
        raise "Medeek Wall Plugin license required. Please activate your license in SketchUp."
      else
        raise "Medeek Wall Plugin error: #{e.message}"
      end
    end

    # Read column attributes
    def self.read_column_attributes(params)
      column_name = params['column_name']
      group_name = params['group_name']

      raise "column_name is required" unless column_name

      medeek = get_medeek_module
      raise "Medeek Wall Plugin not available. Please install and license the plugin." unless medeek

      if group_name
        # Find group by name
        wall_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name == group_name }
        raise "Wall group '#{group_name}' not found" unless wall_group

        attributes = medeek.wall_column_read_attributes(column_name, wall_group)
      else
        # Use selection
        attributes = medeek.wall_column_read_attributes(column_name)
      end

      raise "Failed to read column attributes" unless attributes

      {
        status: 'success',
        column_name: column_name,
        attributes: attributes
      }

    rescue => e
      if e.message.include?("license") || e.message.include?("License")
        raise "Medeek Wall Plugin license required. Please activate your license in SketchUp."
      else
        raise "Medeek Wall Plugin error: #{e.message}"
      end
    end

  end
end
