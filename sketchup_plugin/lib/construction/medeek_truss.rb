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
    def self.create(params = {})
      unless available?
        raise "Medeek Truss Plugin not installed. Please install from SketchUp Extension Warehouse."
      end

      span_ft = params['span'] ? params['span'].to_f : 24.0  # Default 24 feet
      span = span_ft * 12.0  # Convert feet to inches
      pitch = params['pitch'] || "6:12"
      truss_type = params['type'] || 'fink'
      origin_arr = params['origin']
      top_plate_corners = params['top_plate_corners']  # Array of 4 points from existing geometry
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

        # Call Medeek API ONCE - it creates all trusses to fill the parallelogram
        result = medeek.common_truss_draw(pitch_numeric, medeek_truss_type, pts)

        SU_MCP.model.commit_operation

        if result
          {
            status: 'created',
            engine: 'medeek',
            truss_type: medeek_truss_type,
            span_ft: span_ft,
            pitch: pitch,
            spacing: spacing,
            building_depth_ft: (building_depth / 12.0).round(2),
            message: "Created #{medeek_truss_type} trusses using Medeek Truss Plugin (#{span_ft}' span × #{(building_depth / 12.0).round(2)}' depth, #{spacing}\" OC)"
          }
        else
          {
            status: 'failed',
            engine: 'medeek',
            message: "Medeek Truss Plugin failed to create trusses"
          }
        end

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

    private

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
