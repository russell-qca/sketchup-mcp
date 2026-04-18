# frozen_string_literal: true

module Construction
  # MedeekTruss - Wrapper for Medeek Truss Plugin API
  # Uses professional Medeek Truss Plugin when available
  # Falls back to built-in implementation if not installed
  class MedeekTruss
    # Check if Medeek Truss Plugin is installed
    def self.available?
      begin
        defined?(Medeek_Engineering_Inc_Extensions::MedeekTrussPlugin::MedeekMethods)
      rescue
        false
      end
    end

    # Create roof trusses using Medeek Truss Plugin
    #
    # IMPORTANT: Medeek Truss API Workflow
    # 1. common_truss_draw(pitch, type, pts) - Creates truss with DEFAULT settings (accepts only pitch, type, and geometry)
    # 2. common_set_attribute(param, value, group, regen) - Modifies each parameter
    #    - Set regen=false for all attributes except the last one
    #    - Set regen=true on the final attribute to trigger single regeneration
    def self.create(params = {})
      unless available?
        raise "Medeek Truss Plugin not installed. Please install from SketchUp Extension Warehouse."
      end

      # STEP 0: Auto-detect walls and get top plate geometry
      # This ensures we always use the correct wall height, similar to foundation auto-detection
      top_plate_corners = params['top_plate_corners']

      if !top_plate_corners
        begin
          # Try to automatically get wall information
          wall_info = Construction::MedeekWall.get_wall_info({})

          if wall_info && wall_info[:status] == 'success'
            top_plate_z = wall_info[:top_plate_z]
            wall_start = wall_info[:wall_start]
            wall_end = wall_info[:wall_end]

            SU_MCP.log "[SU_MCP] Auto-detected wall: top_plate_z = #{top_plate_z}\", length = #{wall_info[:wall_length]}\""

            # Calculate the 4 corners based on wall geometry and building depth
            building_depth_ft = params['building_depth'] ? params['building_depth'].to_f : 24.0
            building_depth = building_depth_ft * 12.0

            # Create rectangle at top plate height
            top_plate_corners = [
              [wall_start[0], wall_start[1], top_plate_z],  # Front left
              [wall_end[0], wall_end[1], top_plate_z],      # Front right
              [wall_end[0], wall_end[1] + building_depth, top_plate_z],  # Back right
              [wall_start[0], wall_start[1] + building_depth, top_plate_z]  # Back left
            ]

            SU_MCP.log "[SU_MCP] Auto-generated top plate corners from wall geometry"
          end
        rescue => e
          SU_MCP.log "[SU_MCP] No walls auto-detected (this is OK if creating trusses from scratch): #{e.message}"
        end
      end

      # Basic geometry parameters
      span_ft = params['span'] ? params['span'].to_f : 24.0  # Default 24 feet
      span = span_ft * 12.0  # Convert feet to inches
      pitch = params['pitch'] || "6:12"
      truss_type = params['type'] || 'fink'
      origin_arr = params['origin']
      building_depth_ft = params['building_depth'] ? params['building_depth'].to_f : 24.0  # Default 24 feet
      spacing = params['spacing'] ? params['spacing'].to_f : 24.0  # inches OC
      overhang = params['overhang'] ? params['overhang'].to_f : 12.0  # inches


      # Parse pitch from "6:12" format to numeric (6.0)
      rise, run = parse_pitch(pitch)
      pitch_numeric = rise.to_f  # Medeek expects just the rise (assumes /12)

      # Map our truss type to Medeek's format (case sensitive!)
      medeek_truss_type = map_truss_type(truss_type)

      # Origin point (left wall location)
      origin = origin_arr ? SU_MCP.parse_point(origin_arr) : SU_MCP::ORIGIN

      raise "Span must be positive" if span <= 0
      raise "Pitch must be between 0.25 and 24.0" if pitch_numeric < 0.25 || pitch_numeric > 24.0
      raise "Building depth must be positive" if building_depth_ft <= 0

      SU_MCP.model.start_operation('MCP Create Roof Trusses (Medeek)', true)

      begin
        # Get Medeek API
        medeek = Medeek_Engineering_Inc_Extensions::MedeekTrussPlugin::MedeekMethods

        # Determine the 4 corner points for Medeek
        if top_plate_corners && top_plate_corners.length == 4
          # Use the provided top plate corners directly - Claude found an existing face
          # IMPORTANT: Pass these AS-IS without modification
          pts = top_plate_corners
          # Calculate building depth from provided points (distance from pt0 to pt3)
          pt0 = Geom::Point3d.new(pts[0])
          pt3 = Geom::Point3d.new(pts[3])
          building_depth = pt0.distance(pt3)
          SU_MCP.log "[SU_MCP] Using provided top plate corners (existing geometry), depth=#{(building_depth/12.0).round(2)}'"
        else
          # Calculate points based on origin, span, and building depth
          building_depth = building_depth_ft * 12.0  # Convert feet to inches

          # Points array: 4 corners of the rectangular top plate
          # [front_left, front_right, back_right, back_left]
          pts = [
            [origin.x, origin.y, origin.z],                           # Front left
            [origin.x + span, origin.y, origin.z],                    # Front right
            [origin.x + span, origin.y + building_depth, origin.z],   # Back right
            [origin.x, origin.y + building_depth, origin.z]           # Back left
          ]
          SU_MCP.log "[SU_MCP] Calculated top plate: span=#{span_ft}', depth=#{building_depth_ft}'"
        end

        # STEP 1: Call Medeek API ONCE - it creates all trusses with DEFAULT settings
        result = medeek.common_truss_draw(pitch_numeric, medeek_truss_type, pts)

        unless result
          SU_MCP.model.abort_operation
          return {
            status: 'failed',
            engine: 'medeek',
            message: "Medeek Truss Plugin failed to create trusses"
          }
        end

        # STEP 2: Get the created truss assembly group
        # Medeek API returns the created group directly
        truss_group = nil

        if result.is_a?(Sketchup::Group)
          # Result is the group itself - use it directly
          truss_group = result
          SU_MCP.log "[SU_MCP] Using truss group returned by Medeek API: #{truss_group.name}"
        else
          # Fallback: Search for the newly created truss assembly
          # Find all current truss assemblies and use the most recently created one
          all_trusses = SU_MCP.model.active_entities.grep(Sketchup::Group).select { |g| g.name =~ /COMMON_TRUSS_ASSEMBLY_/ }

          # Sort by entityID (higher ID = more recently created) and take the last one
          truss_group = all_trusses.max_by { |g| g.entityID }

          if truss_group
            SU_MCP.log "[SU_MCP] Found most recent truss assembly by entityID: #{truss_group.name} (ID: #{truss_group.entityID})"
          end
        end

        # Truss created successfully
        SU_MCP.model.commit_operation

        {
          status: 'created',
          engine: 'medeek',
          truss_type: medeek_truss_type,
          group_name: truss_group ? truss_group.name : 'unknown',
          span_ft: span_ft,
          pitch: pitch,
          spacing: spacing,
          building_depth_ft: (building_depth / 12.0).round(2),
          message: "Created #{medeek_truss_type} trusses using Medeek Truss Plugin (#{span_ft}' span × #{(building_depth / 12.0).round(2)}' depth, #{spacing}\" OC). Use modify_truss to add sheathing, fascia, etc."
        }

      rescue => e
        SU_MCP.model.abort_operation

        # Check if error is due to missing license
        if e.message.include?("license") || e.message.include?("License")
          raise "Medeek Truss Plugin license required. Please activate your license in SketchUp."
        else
          raise "Medeek Truss Plugin error: #{e.message}"
        end
      end
    end

    # Read all attributes from a truss assembly
    def self.read_truss_attributes(params)
      group_name = params['group_name']

      unless available?
        raise "Medeek Truss Plugin not installed."
      end

      medeek = Medeek_Engineering_Inc_Extensions::MedeekTrussPlugin::MedeekMethods

      if group_name
        # Find group by name
        truss_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name == group_name }
        raise "Truss group '#{group_name}' not found" unless truss_group

        attributes = medeek.truss_read_attributes(truss_group)
      else
        # Use selection or find any truss
        truss_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name =~ /TRUSS_ASSEMBLY/ }
        raise "No truss assembly found" unless truss_group

        attributes = medeek.truss_read_attributes(truss_group)
      end

      raise "Failed to read truss attributes" unless attributes

      {
        status: 'success',
        group_name: truss_group.name,
        attributes: attributes
      }
    end

    # Read a single attribute from a truss assembly
    def self.read_truss_attribute(params)
      attribute_name = params['attribute_name']
      group_name = params['group_name']

      raise "attribute_name is required" unless attribute_name

      unless available?
        raise "Medeek Truss Plugin not installed."
      end

      medeek = Medeek_Engineering_Inc_Extensions::MedeekTrussPlugin::MedeekMethods

      if group_name
        # Find group by name
        truss_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name == group_name }
        raise "Truss group '#{group_name}' not found" unless truss_group

        value = medeek.truss_get_attribute(attribute_name, truss_group)
      else
        # Find any truss
        truss_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name =~ /TRUSS_ASSEMBLY/ }
        raise "No truss assembly found" unless truss_group

        value = medeek.truss_get_attribute(attribute_name, truss_group)
      end

      {
        status: 'success',
        attribute_name: attribute_name,
        value: value
      }
    end

    # Modify a truss assembly attribute
    def self.modify_truss_attribute(params)
      group_name = params['group_name']
      attribute_name = params['attribute_name']
      value = params['value']
      regenerate = params['regenerate'].nil? ? true : params['regenerate']

      raise "attribute_name is required" unless attribute_name
      raise "value is required" if value.nil?

      unless available?
        raise "Medeek Truss Plugin not installed."
      end

      # Convert fraction strings to decimals for thickness attributes
      if attribute_name == 'SHEATHING_THICKNESS' || attribute_name == 'WALLSHEATHTHK'
        value = convert_fraction_to_decimal(value)
      end

      SU_MCP.model.start_operation('Modify Truss Attribute', true)

      medeek = Medeek_Engineering_Inc_Extensions::MedeekTrussPlugin::MedeekMethods

      if group_name
        # Find group by name
        truss_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name == group_name }
        raise "Truss group '#{group_name}' not found" unless truss_group

        result = medeek.truss_set_attribute(attribute_name, value, truss_group, regenerate)
      else
        # Find any truss
        truss_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name =~ /TRUSS_ASSEMBLY/ }
        raise "No truss assembly found" unless truss_group

        result = medeek.truss_set_attribute(attribute_name, value, truss_group, regenerate)
      end

      raise "Failed to set truss attribute" unless result

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
        raise "Medeek Truss Plugin license required. Please activate your license in SketchUp."
      else
        raise "Medeek Truss Plugin error: #{e.message}"
      end
    end

    # Modify multiple truss attributes at once (batch modification)
    # This is the PREFERRED method when changing multiple related attributes
    # (e.g., enabling advanced roof options and sheathing together)
    # It sets all attributes with regen=false, then regenerates once at the end
    def self.modify_truss(params)
      group_name = params['group_name']

      raise "group_name is required" unless group_name

      unless available?
        raise "Medeek Truss Plugin not installed."
      end

      SU_MCP.model.start_operation('Modify Truss Assembly', true)

      medeek = Medeek_Engineering_Inc_Extensions::MedeekTrussPlugin::MedeekMethods

      # Find group by name
      truss_group = SU_MCP.model.active_entities.grep(Sketchup::Group).find { |g| g.name == group_name }
      raise "Truss group '#{group_name}' not found" unless truss_group

      SU_MCP.log "[SU_MCP] Modifying truss assembly: #{group_name}"

      # Build list of attributes to modify
      attributes_to_set = []

      # CRITICAL: Detect if ANY advanced roof features are requested
      # These features require ADVROOFOPTIONS='YES' to be set FIRST
      needs_adv_roof_options = (
        params['sheathing_option'] || params['sheathing_thickness'] ||
        params['fascia_option'] || params['fascia_type'] || params['fascia_width'] || params['fascia_depth'] ||
        params['rakeboard_option'] || params['rake_width'] || params['rake_depth'] || params['overhang_gable'] ||
        params['outlooker_option'] || params['outlooker_spacing'] || params['outlooker_size'] ||
        params['heelblock_option'] || params['heelblock_orient'] ||
        params['roofcladding_option'] || params['roofclad_ext'] || params['roofclad_mat'] || params['roofclad_thk'] ||
        params['ridgecap_option'] ||
        params['wallcladding_option'] || params['wallclad_mat'] || params['wallclad_thk'] ||
        params['soffit_cut'] ||
        params['roof_return'] || params['return_type'] || params['return_ext'] || params['return_length'] ||
        params['roof_batten'] ||
        params['gutter_option'] || params['gutter_type'] || params['gutter_voffset'] || params['gutter_ext'] ||
        params['downspout_option'] || params['dsp_length'] || params['dsp_type'] ||
        params['gutter_wrap_option'] ||
        params['roofsheath_mat'] || params['wallsheath_mat'] || params['wallsheath_thk'] ||
        params['gable_wall_option'] || params['gypsum_option'] || params['insul_option']
      )

      # If advanced features requested OR explicitly set, ensure ADVROOFOPTIONS is YES and set it FIRST
      if needs_adv_roof_options || params['adv_roof_options'] == 'YES'
        attributes_to_set << ['ADVROOFOPTIONS', 'YES']
        SU_MCP.log "[SU_MCP] Auto-enabling ADVROOFOPTIONS='YES' (required for advanced roof features)"
      elsif params['adv_roof_options'] == 'NO'
        attributes_to_set << ['ADVROOFOPTIONS', 'NO']
      end

      # Overhangs
      attributes_to_set << ['OVERHANGL', params['overhang_left'].to_f] if params['overhang_left']
      if params['overhang_right']
        overhang_right_value = params['overhang_right'].is_a?(String) ? params['overhang_right'] : params['overhang_right'].to_f
        attributes_to_set << ['OVERHANGR', overhang_right_value]
      end

      # Chord/web dimensions
      attributes_to_set << ['TCD', params['top_chord_depth'].to_f] if params['top_chord_depth']
      attributes_to_set << ['BCD', params['bottom_chord_depth'].to_f] if params['bottom_chord_depth']
      attributes_to_set << ['WEBD', params['web_depth'].to_f] if params['web_depth']
      attributes_to_set << ['PLY', params['ply'].to_i] if params['ply']

      # Raised heel
      attributes_to_set << ['RAISEDHEEL', params['raised_heel']] if params['raised_heel']
      attributes_to_set << ['USRHH', params['raised_heel_height'].to_f] if params['raised_heel_height']

      # Truss spacing
      attributes_to_set << ['TRUSS_SPACING', params['truss_spacing'].to_f] if params['truss_spacing']

      # Gable truss
      attributes_to_set << ['GABLETRUSSINPUT', params['gable_truss_input']] if params['gable_truss_input']

      # Web spacing
      attributes_to_set << ['VERTSPACING', params['vert_spacing'].to_f] if params['vert_spacing']

      # Sheathing
      attributes_to_set << ['SHEATHING_OPTION', params['sheathing_option']] if params['sheathing_option']
      if params['sheathing_thickness']
        # Convert fraction string like "15/32" to decimal like 0.46875
        sheathing_decimal = convert_fraction_to_decimal(params['sheathing_thickness'])
        attributes_to_set << ['SHEATHING_THICKNESS', sheathing_decimal]
      end

      # Gable wall
      attributes_to_set << ['GABLEWALL_OPTION', params['gable_wall_option']] if params['gable_wall_option']

      # Fascia
      attributes_to_set << ['FASCIA_OPTION', params['fascia_option']] if params['fascia_option']
      attributes_to_set << ['FASCIA_TYPE', params['fascia_type']] if params['fascia_type']
      attributes_to_set << ['FASCIA_WIDTH', params['fascia_width'].to_f] if params['fascia_width']
      attributes_to_set << ['FASCIA_DEPTH', params['fascia_depth'].to_f] if params['fascia_depth']

      # Rake board
      attributes_to_set << ['RAKEBOARD_OPTION', params['rakeboard_option']] if params['rakeboard_option']
      attributes_to_set << ['OVERHANG_GABLE', params['overhang_gable'].to_f] if params['overhang_gable']
      attributes_to_set << ['RAKE_WIDTH', params['rake_width'].to_f] if params['rake_width']
      attributes_to_set << ['RAKE_DEPTH', params['rake_depth'].to_f] if params['rake_depth']

      # Outlooker
      attributes_to_set << ['OUTLOOKER_OPTION', params['outlooker_option']] if params['outlooker_option']
      attributes_to_set << ['OUTLOOKER_SPACING', params['outlooker_spacing'].to_f] if params['outlooker_spacing']
      attributes_to_set << ['OUTLOOKER_SIZE', params['outlooker_size']] if params['outlooker_size']
      attributes_to_set << ['OUTLOOKER_ORIENT', params['outlooker_orient']] if params['outlooker_orient']
      attributes_to_set << ['OUTLOOKER_PEAK', params['outlooker_peak']] if params['outlooker_peak']

      # Heel block
      attributes_to_set << ['HEELBLOCK_OPTION', params['heelblock_option']] if params['heelblock_option']
      attributes_to_set << ['HEELBLOCK_ORIENT', params['heelblock_orient']] if params['heelblock_orient']

      # Roof cladding
      attributes_to_set << ['ROOFCLADDING_OPTION', params['roofcladding_option']] if params['roofcladding_option']
      attributes_to_set << ['ROOFCLAD_EXT', params['roofclad_ext'].to_f] if params['roofclad_ext']

      # Ridge cap
      attributes_to_set << ['RIDGECAP_OPTION', params['ridgecap_option']] if params['ridgecap_option']

      # Wall cladding
      attributes_to_set << ['WALLCLADDING_OPTION', params['wallcladding_option']] if params['wallcladding_option']

      # Soffit cut
      attributes_to_set << ['SOFFIT_CUT', params['soffit_cut']] if params['soffit_cut']

      # Roof return
      attributes_to_set << ['ROOF_RETURN', params['roof_return']] if params['roof_return']
      attributes_to_set << ['RETURN_TYPE', params['return_type']] if params['return_type']
      attributes_to_set << ['PITCH3', params['pitch3']] if params['pitch3']
      attributes_to_set << ['RETURN_EXT', params['return_ext'].to_f] if params['return_ext']
      attributes_to_set << ['RETURN_LENGTH', params['return_length'].to_f] if params['return_length']

      # Roof batten
      attributes_to_set << ['ROOF_BATTEN', params['roof_batten']] if params['roof_batten']

      # Gypsum
      attributes_to_set << ['GYPSUM_OPTION', params['gypsum_option']] if params['gypsum_option']

      # Gutter
      attributes_to_set << ['GUTTER_OPTION', params['gutter_option']] if params['gutter_option']
      attributes_to_set << ['GUTTER_TYPE', params['gutter_type']] if params['gutter_type']
      attributes_to_set << ['GUTTER_VOFFSET', params['gutter_voffset'].to_f] if params['gutter_voffset']
      attributes_to_set << ['GUTTER_EXT', params['gutter_ext'].to_f] if params['gutter_ext']

      # Downspout
      attributes_to_set << ['DOWNSPOUT_OPTION', params['downspout_option']] if params['downspout_option']
      attributes_to_set << ['DSP_LENGTH', params['dsp_length'].to_f] if params['dsp_length']
      attributes_to_set << ['DSP_TYPE', params['dsp_type']] if params['dsp_type']

      # Gutter wrap
      attributes_to_set << ['GUTTER_WRAP_OPTION', params['gutter_wrap_option']] if params['gutter_wrap_option']

      # Insulation
      attributes_to_set << ['INSUL_OPTION', params['insul_option']] if params['insul_option']

      # Materials
      attributes_to_set << ['WALLSHEATH_MAT', params['wallsheath_mat']] if params['wallsheath_mat']
      attributes_to_set << ['WALLCLAD_MAT', params['wallclad_mat']] if params['wallclad_mat']
      attributes_to_set << ['ROOFSHEATH_MAT', params['roofsheath_mat']] if params['roofsheath_mat']
      attributes_to_set << ['ROOFCLAD_MAT', params['roofclad_mat']] if params['roofclad_mat']

      # Material thicknesses
      if params['wallsheath_thk']
        # Convert fraction string to decimal if needed
        wallsheath_decimal = convert_fraction_to_decimal(params['wallsheath_thk'])
        attributes_to_set << ['WALLSHEATHTHK', wallsheath_decimal]
      end
      attributes_to_set << ['WALLCLAD_THK', params['wallclad_thk'].to_f] if params['wallclad_thk']
      attributes_to_set << ['ROOFCLAD_THK', params['roofclad_thk'].to_f] if params['roofclad_thk']

      if attributes_to_set.empty?
        SU_MCP.model.abort_operation
        raise "No attributes to modify. Please provide at least one parameter to change."
      end

      # Set all attributes with regen=false except the last one
      attributes_to_set.each_with_index do |(attr_name, attr_value), index|
        is_last = (index == attributes_to_set.length - 1)
        SU_MCP.log "[SU_MCP]   Setting #{attr_name} = #{attr_value} (regen: #{is_last})"
        medeek.truss_set_attribute(attr_name, attr_value, truss_group, is_last)
      end

      SU_MCP.model.commit_operation

      {
        status: 'modified',
        engine: 'medeek',
        group_name: truss_group.name,
        attributes_modified: attributes_to_set.length,
        message: "Modified truss assembly '#{truss_group.name}' - updated #{attributes_to_set.length} parameter(s)"
      }

    rescue => e
      SU_MCP.model.abort_operation

      if e.message.include?("license") || e.message.include?("License")
        raise "Medeek Truss Plugin license required. Please activate your license in SketchUp."
      else
        raise "Medeek Truss Plugin error: #{e.message}"
      end
    end

    private

    # Convert fraction string to decimal number
    # Examples: "15/32" -> 0.46875, "1/2" -> 0.5, 0.5 -> 0.5
    def self.convert_fraction_to_decimal(value)
      return value.to_f if value.is_a?(Numeric)

      value_str = value.to_s.strip

      # Check if it's already a decimal number
      return value_str.to_f unless value_str.include?('/')

      # Parse fraction like "15/32"
      parts = value_str.split('/')
      return 0.0 if parts.length != 2

      numerator = parts[0].to_f
      denominator = parts[1].to_f
      return 0.0 if denominator == 0.0

      numerator / denominator
    end

    # Parse pitch like "6:12" or "6/12" into rise/run ratio
    def self.parse_pitch(pitch_str)
      parts = pitch_str.to_s.split(/[:\/]/)
      rise = parts[0].to_f
      run = parts.length > 1 ? parts[1].to_f : 12.0
      [rise, run]
    end

    # Map our truss type names to Medeek's format (case sensitive!)
    def self.map_truss_type(type)
      mapping = {
        'king' => 'King Post',
        'queen' => 'Queen Post',
        'fink' => 'Fink',
        'howe' => 'Howe',
        'fan' => 'Fan',
        'mod_queen' => 'Mod Queen',
        'double_fink' => 'Double Fink',
        'double_howe' => 'Double Howe',
        'mod_fan' => 'Mod Fan',
        'triple_fink' => 'Triple Fink',
        'triple_howe' => 'Triple Howe',
        'quad_fink' => 'Quad Fink',
        'quad_howe' => 'Quad Howe',
        'penta_howe' => 'Penta Howe'
      }

      medeek_type = mapping[type.to_s.downcase]

      unless medeek_type
        raise "Unknown truss type '#{type}'. Supported types: #{mapping.keys.join(', ')}"
      end

      medeek_type
    end
  end
end
