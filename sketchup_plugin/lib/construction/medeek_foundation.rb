# frozen_string_literal: true

module Construction
  # MedeekFoundation - Wrapper for Medeek Foundation Plugin API
  # Uses professional Medeek Foundation Plugin when available
  # Falls back to built-in implementation if not installed
  class MedeekFoundation
    # Check if Medeek Foundation Plugin is installed
    def self.available?
      begin
        defined?(Medeek_Engineering_Inc_Extensions::MedeekFoundationPlugin::Sog::MedeekMethods)
      rescue
        false
      end
    end

    # Create slab-on-grade foundation using Medeek Foundation Plugin
    #
    # IMPORTANT: Medeek API Workflow
    # 1. sog_draw(pts) - Creates foundation with DEFAULT settings (only accepts geometry).
    #    DO NOT pass any other parameters to the sog_draw method.  You must first create the
    #    default slab then modify it with the sog_set_attribute method.
    #    after create the slab be sure to make a call to sketchup to get the foundation entity id.
    # 2. sog_set_attribute(param, value, group, regen) - Modifies each parameter
    #    - Set regen=false for all attributes except the last one
    #    - Set regen=true on the final attribute to trigger single regeneration
    #    - it is important to pass the group.
    # This method handles both steps automatically in a single call.
    def self.create(params = {})
      unless available?
        raise "Medeek Foundation Plugin not installed. Please install from SketchUp Extension Warehouse."
      end

      # Extract parameters
      outline_points = params['outline_points']  # Array of [x,y,z] points defining foundation perimeter
      foundation_depth = params['foundation_depth'] ? params['foundation_depth'].to_f : 24.0  # inches
      slab_thickness = params['slab_thickness'] ? params['slab_thickness'].to_f : 4.0  # inches
      footing_width = params['footing_width'] ? params['footing_width'].to_f : 16.0  # inches

      # Optional garage curb parameters
      garage_curb = params['garage_curb'] == true
      curb_width = params['curb_width'] ? params['curb_width'].to_f : 4.0  # inches
      curb_height = params['curb_height'] ? params['curb_height'].to_f : 4.0  # inches

      # Optional rebar parameters
      rebar_enabled = params['rebar_enabled'] == true
      top_bar_enabled = params['top_bar_enabled'] == true
      top_bar_diameter = params['top_bar_diameter'] ? params['top_bar_diameter'].to_f : 0.5  # inches
      top_bar_quantity = params['top_bar_quantity'] ? params['top_bar_quantity'].to_i : 2
      bottom_bar_enabled = params['bottom_bar_enabled'] == true
      bottom_bar_diameter = params['bottom_bar_diameter'] ? params['bottom_bar_diameter'].to_f : 0.5  # inches
      bottom_bar_quantity = params['bottom_bar_quantity'] ? params['bottom_bar_quantity'].to_i : 2
      slab_reinforcement_enabled = params['slab_reinforcement_enabled'] == true
      slab_reinforcement_type = params['slab_reinforcement_type'] || '6X6-W1.4XW1.4'  # Default welded wire mesh
      slab_reinforcement_spacing = params['slab_reinforcement_spacing'] ? params['slab_reinforcement_spacing'].to_f : 12.0  # inches

      # Optional anchor bolt parameters
      anchor_bolts_enabled = params['anchor_bolts_enabled'] == true
      bolt_size = params['bolt_size'] || '12'  # Bolt length in inches: "10", "12", "14"
      bolt_diameter = params['bolt_diameter'] || '1/2'  # Bolt diameter: "1/2", "5/8"
      washer_type = params['washer_type'] || '2x2'  # Washer size: "2x2", "3x3"
      bolt_spacing_ft = params['bolt_spacing_ft'] ? params['bolt_spacing_ft'].to_f : 6.0  # feet on center
      sill_width = params['sill_width'] ? params['sill_width'].to_f : 3.5  # inches (2x4 nominal)
      sill_thickness = params['sill_thickness'] ? params['sill_thickness'].to_f : 1.5  # inches (2x4 actual)
      corner_distance = params['corner_distance'] ? params['corner_distance'].to_f : 12.0  # inches from corner

      # Optional FPSF insulation parameters
      fpsf_enabled = params['fpsf_enabled'] == true
      insulation_type = params['insulation_type'] || 'None'  # "Vertical Only", "Vert. and Horz.", "None"
      vertical_insulation = params['vertical_insulation'] ? params['vertical_insulation'].to_f : 2.0  # inches
      wing_insulation = params['wing_insulation'] ? params['wing_insulation'].to_f : 2.0  # inches
      corner_insulation = params['corner_insulation'] ? params['corner_insulation'].to_f : 2.0  # inches
      dim_a = params['dim_a'] ? params['dim_a'].to_f : 24.0  # inches
      dim_b = params['dim_b'] ? params['dim_b'].to_f : 24.0  # inches
      dim_c = params['dim_c'] ? params['dim_c'].to_f : 24.0  # inches

      # Optional slab insulation parameters
      slab_insulation_enabled = params['slab_insulation_enabled'] == true
      slab_insulation = params['slab_insulation'] ? params['slab_insulation'].to_f : 2.0  # inches

      # Optional subbase parameters
      subbase_enabled = params['subbase_enabled'] == true
      subbase_depth = params['subbase_depth'] ? params['subbase_depth'].to_f : 4.0  # inches
      subbase_material = params['subbase_material'] || 'Gravel'  # "Gravel", "Stone1", "corrugated_metal"

      # Optional drain parameter
      drain_enabled = params['drain_enabled'] == true

      # Validation
      raise "Outline points required" unless outline_points && outline_points.length >= 3
      raise "Foundation depth must be positive" if foundation_depth <= 0
      raise "Slab thickness must be positive" if slab_thickness <= 0
      raise "Footing width must be positive" if footing_width <= 0

      # Validate rebar parameters
      if rebar_enabled
        valid_bar_quantities = [1, 2, 3]

        if top_bar_enabled
          raise "Invalid top_bar_quantity '#{top_bar_quantity}'. Must be one of: #{valid_bar_quantities.join(', ')}" unless valid_bar_quantities.include?(top_bar_quantity)
        end

        if bottom_bar_enabled
          raise "Invalid bottom_bar_quantity '#{bottom_bar_quantity}'. Must be one of: #{valid_bar_quantities.join(', ')}" unless valid_bar_quantities.include?(bottom_bar_quantity)
        end

        if slab_reinforcement_enabled
          valid_slab_reinf_types = ['#3-BAR', '#4-BAR', '#5-BAR', '#6-BAR', '#7-BAR', '#8-BAR', '#9-BAR', '#10-BAR', '#11-BAR', '#14-BAR', '#18-BAR', '6X6-W2.9XW2.9', '6X6-W1.4XW1.4']
          raise "Invalid slab_reinforcement_type '#{slab_reinforcement_type}'. Must be one of: #{valid_slab_reinf_types.join(', ')}" unless valid_slab_reinf_types.include?(slab_reinforcement_type)
        end
      end

      # Validate anchor bolt parameters
      if anchor_bolts_enabled
        valid_bolt_sizes = ['10', '12', '14']
        raise "Invalid bolt_size '#{bolt_size}'. Must be one of: #{valid_bolt_sizes.join(', ')}" unless valid_bolt_sizes.include?(bolt_size)

        valid_bolt_diameters = ['1/2', '5/8']
        raise "Invalid bolt_diameter '#{bolt_diameter}'. Must be one of: #{valid_bolt_diameters.join(', ')}" unless valid_bolt_diameters.include?(bolt_diameter)

        valid_washer_types = ['2x2', '3x3']
        raise "Invalid washer_type '#{washer_type}'. Must be one of: #{valid_washer_types.join(', ')}" unless valid_washer_types.include?(washer_type)
      end

      # Validate FPSF insulation parameters
      if fpsf_enabled
        valid_insulation_types = ['Vertical Only', 'Vert. and Horz.', 'None']
        raise "Invalid insulation_type '#{insulation_type}'. Must be one of: #{valid_insulation_types.join(', ')}" unless valid_insulation_types.include?(insulation_type)
      end

      # Validate subbase parameters
      if subbase_enabled
        valid_subbase_materials = ['Gravel', 'Stone1', 'corrugated_metal']
        raise "Invalid subbase_material '#{subbase_material}'. Must be one of: #{valid_subbase_materials.join(', ')}" unless valid_subbase_materials.include?(subbase_material)
      end

      SU_MCP.model.start_operation('MCP Create Foundation (Medeek)', true)

      begin
        # Get Medeek Foundation API
        medeek = Medeek_Engineering_Inc_Extensions::MedeekFoundationPlugin::Sog::MedeekMethods

        # Convert points to proper format if needed
        pts = outline_points.map do |pt|
          if pt.is_a?(Array) && pt.length == 3
            pt
          elsif pt.is_a?(Geom::Point3d)
            [pt.x, pt.y, pt.z]
          else
            raise "Invalid point format: #{pt.inspect}"
          end
        end

        SU_MCP.log "[SU_MCP] Creating foundation with Medeek: #{pts.length} points, depth=#{foundation_depth}\""

        # STEP 1: Create the foundation with DEFAULT settings only (Medeek only accepts geometry)
        result = medeek.sog_draw(pts)

        if result
          # Get the created assembly - try selection first, then search all groups
          foundation_group = SU_MCP.model.selection.grep(Sketchup::Group).last

          # If not in selection, search for the foundation group by name pattern
          unless foundation_group
            SU_MCP.log "[SU_MCP] Foundation not in selection, searching by name pattern..."
            foundation_group = SU_MCP.model.entities.grep(Sketchup::Group).reverse.find do |g|
              g.name && g.name.include?('FOUNDATION_SOG_POLYGON_ASSEMBLY')
            end
          end

          unless foundation_group
            SU_MCP.model.abort_operation
            raise "Failed to locate created foundation assembly. The foundation may have been created but could not be found for parameter configuration."
          end

          SU_MCP.log "[SU_MCP] Found foundation group: #{foundation_group.name}"

          # STEP 2: Modify parameters using sog_set_attribute (parameters can ONLY be changed AFTER creation)
          # Set all attributes with regen=false, then set the last one with regen=true to regenerate once

          # Set foundation depth (FDEPTH)
          medeek.sog_set_attribute('FDEPTH', foundation_depth, foundation_group, false)

          # Set slab thickness (SLABTHICKNESS)
          medeek.sog_set_attribute('SLABTHICKNESS', slab_thickness, foundation_group, false)

          # Set footing width (FTGWIDTH) - may be last if no optional features
          last_regen = !garage_curb && !rebar_enabled && !anchor_bolts_enabled
          medeek.sog_set_attribute('FTGWIDTH', footing_width, foundation_group, last_regen)

          # Set garage curb if requested
          if garage_curb
            medeek.sog_set_attribute('CURBOPTION', 'YES', foundation_group, false)
            medeek.sog_set_attribute('CURBWIDTH', curb_width, foundation_group, false)
            # Set last curb attribute with regen if no rebar or anchor bolts
            last_regen = !rebar_enabled && !anchor_bolts_enabled
            medeek.sog_set_attribute('CURBHEIGHT', curb_height, foundation_group, last_regen)
          end

          # Set rebar options if requested
          if rebar_enabled
            medeek.sog_set_attribute('REBAROPTION', 'YES', foundation_group, false)

            # Top bars
            if top_bar_enabled
              medeek.sog_set_attribute('TOPBAROPTION', 'YES', foundation_group, false)
              medeek.sog_set_attribute('TOPBARDIA', top_bar_diameter, foundation_group, false)
              medeek.sog_set_attribute('TOPBARQTY', top_bar_quantity, foundation_group, false)
            end

            # Bottom bars
            if bottom_bar_enabled
              medeek.sog_set_attribute('BOTTOMBAROPTION', 'YES', foundation_group, false)
              medeek.sog_set_attribute('BOTTOMBARDIA', bottom_bar_diameter, foundation_group, false)
              medeek.sog_set_attribute('BOTTOMBARQTY', bottom_bar_quantity, foundation_group, false)
            end

            # Slab reinforcement - set last attribute with regen if no anchor bolts
            if slab_reinforcement_enabled
              medeek.sog_set_attribute('SLABREINFOPTION', 'YES', foundation_group, false)
              medeek.sog_set_attribute('SLABREINFTYPE', slab_reinforcement_type, foundation_group, false)
              last_regen = !anchor_bolts_enabled
              medeek.sog_set_attribute('SLABREINFSPACING', slab_reinforcement_spacing, foundation_group, last_regen)
            end
          end

          # Set anchor bolt options if requested
          if anchor_bolts_enabled
            medeek.sog_set_attribute('ABOLTOPTION', 'YES', foundation_group, false)
            medeek.sog_set_attribute('BOLTSIZE', bolt_size, foundation_group, false)
            medeek.sog_set_attribute('BOLTDIA', bolt_diameter, foundation_group, false)
            medeek.sog_set_attribute('WASHER', washer_type, foundation_group, false)
            medeek.sog_set_attribute('BOLTSPACING_FT', bolt_spacing_ft, foundation_group, false)
            medeek.sog_set_attribute('SILLWIDTH', sill_width, foundation_group, false)
            medeek.sog_set_attribute('SILLTHICKNESS', sill_thickness, foundation_group, false)
            last_regen = !fpsf_enabled && !slab_insulation_enabled && !subbase_enabled && !drain_enabled
            medeek.sog_set_attribute('CORNERDIST', corner_distance, foundation_group, last_regen)
          end

          # Set FPSF insulation options if requested
          if fpsf_enabled
            medeek.sog_set_attribute('FPSFOPTION', 'YES', foundation_group, false)
            medeek.sog_set_attribute('INSULATION', insulation_type, foundation_group, false)
            medeek.sog_set_attribute('VINSUL', vertical_insulation, foundation_group, false)
            medeek.sog_set_attribute('WINSUL', wing_insulation, foundation_group, false)
            medeek.sog_set_attribute('CINSUL', corner_insulation, foundation_group, false)
            medeek.sog_set_attribute('DIMA', dim_a, foundation_group, false)
            medeek.sog_set_attribute('DIMB', dim_b, foundation_group, false)
            last_regen = !slab_insulation_enabled && !subbase_enabled && !drain_enabled
            medeek.sog_set_attribute('DIMC', dim_c, foundation_group, last_regen)
          end

          # Set slab insulation options if requested
          if slab_insulation_enabled
            medeek.sog_set_attribute('SINSULOPTION', 'YES', foundation_group, false)
            last_regen = !subbase_enabled && !drain_enabled
            medeek.sog_set_attribute('SINSUL', slab_insulation, foundation_group, last_regen)
          end

          # Set subbase options if requested
          if subbase_enabled
            medeek.sog_set_attribute('SUBBASEOPTION', 'YES', foundation_group, false)
            medeek.sog_set_attribute('SUBBASEDEPTH', subbase_depth, foundation_group, false)
            last_regen = !drain_enabled
            medeek.sog_set_attribute('SUBBASEMAT', subbase_material, foundation_group, last_regen)
          end

          # Set drain option if requested - this is always last
          if drain_enabled
            medeek.sog_set_attribute('DRAINOPTION', 'YES', foundation_group, true)
          end

          # The input Z coordinate IS the top-of-slab position
          # This is where wall framing starts, NOT the top of anchor bolts
          origin_z = pts[0][2].to_f  # Z coordinate from first input point
          slab_top_z = origin_z  # Input Z IS the slab top - no calculation needed

          SU_MCP.log "[SU_MCP] Foundation origin Z: #{origin_z}\", slab thickness: #{slab_thickness}\", top of slab Z: #{slab_top_z}\""

          # Tag slab entities for organization
          slab_entities_tagged = tag_slab_entities(foundation_group, slab_thickness, origin_z)

          SU_MCP.model.commit_operation

          {
            status: 'created',
            engine: 'medeek',
            foundation_type: 'slab-on-grade',
            group_name: foundation_group.name,
            foundation_depth: foundation_depth,
            slab_thickness: slab_thickness,
            footing_width: footing_width,
            garage_curb: garage_curb,
            perimeter_length_ft: calculate_perimeter(pts) / 12.0,
            slab_top_z: slab_top_z,
            message: "Created slab-on-grade foundation '#{foundation_group.name}' using Medeek Foundation Plugin (depth: #{foundation_depth}\", slab: #{slab_thickness}\", footing: #{footing_width}\", top at Z=#{slab_top_z.round(2)}\")"
          }
        else
          {
            status: 'failed',
            engine: 'medeek',
            message: "Medeek Foundation Plugin failed to create foundation"
          }
        end

      rescue => e
        SU_MCP.model.abort_operation

        # Check if error is due to missing license
        if e.message.include?("license") || e.message.include?("License")
          raise "Medeek Foundation Plugin license required. Please activate your license in SketchUp."
        else
          raise "Medeek Foundation Plugin error: #{e.message}"
        end
      end
    end

    # Modify existing slab-on-grade foundation
    #
    # IMPORTANT: This modifies an EXISTING foundation created by Medeek
    # Takes the foundation group_name and parameters to change
    # Uses sog_set_attribute with regen=true on the last parameter
    def self.modify(params = {})
      unless available?
        raise "Medeek Foundation Plugin not installed. Please install from SketchUp Extension Warehouse."
      end

      # Extract foundation identifier
      group_name = params['group_name']
      raise "Foundation group_name required" unless group_name

      # Find the foundation group
      foundation_group = SU_MCP.model.entities.grep(Sketchup::Group).find do |g|
        g.name == group_name
      end

      unless foundation_group
        raise "Foundation '#{group_name}' not found. Use read_foundation_attributes to list available foundations."
      end

      SU_MCP.log "[SU_MCP] Modifying foundation: #{group_name}"

      SU_MCP.model.start_operation('MCP Modify Foundation (Medeek)', true)

      begin
        # Get Medeek Foundation API
        medeek = Medeek_Engineering_Inc_Extensions::MedeekFoundationPlugin::Sog::MedeekMethods

        # Build list of attributes to modify
        attributes_to_set = []

        # Basic parameters
        attributes_to_set << ['FDEPTH', params['foundation_depth'].to_f] if params['foundation_depth']
        attributes_to_set << ['SLABTHICKNESS', params['slab_thickness'].to_f] if params['slab_thickness']
        attributes_to_set << ['FTGWIDTH', params['footing_width'].to_f] if params['footing_width']

        # Garage curb
        if params['garage_curb'] == true
          attributes_to_set << ['CURBOPTION', 'YES']
          attributes_to_set << ['CURBWIDTH', params['curb_width'].to_f] if params['curb_width']
          attributes_to_set << ['CURBHEIGHT', params['curb_height'].to_f] if params['curb_height']
        elsif params['garage_curb'] == false
          attributes_to_set << ['CURBOPTION', 'NO']
        end

        # Rebar options
        if params['rebar_enabled'] == true
          attributes_to_set << ['REBAROPTION', 'YES']

          if params['top_bar_enabled'] == true
            attributes_to_set << ['TOPBAROPTION', 'YES']
            attributes_to_set << ['TOPBARDIA', params['top_bar_diameter'].to_f] if params['top_bar_diameter']
            if params['top_bar_quantity']
              valid_bar_quantities = [1, 2, 3]
              raise "Invalid top_bar_quantity '#{params['top_bar_quantity']}'. Must be one of: #{valid_bar_quantities.join(', ')}" unless valid_bar_quantities.include?(params['top_bar_quantity'].to_i)
              attributes_to_set << ['TOPBARQTY', params['top_bar_quantity'].to_i]
            end
          elsif params['top_bar_enabled'] == false
            attributes_to_set << ['TOPBAROPTION', 'NO']
          end

          if params['bottom_bar_enabled'] == true
            attributes_to_set << ['BOTTOMBAROPTION', 'YES']
            attributes_to_set << ['BOTTOMBARDIA', params['bottom_bar_diameter'].to_f] if params['bottom_bar_diameter']
            if params['bottom_bar_quantity']
              valid_bar_quantities = [1, 2, 3]
              raise "Invalid bottom_bar_quantity '#{params['bottom_bar_quantity']}'. Must be one of: #{valid_bar_quantities.join(', ')}" unless valid_bar_quantities.include?(params['bottom_bar_quantity'].to_i)
              attributes_to_set << ['BOTTOMBARQTY', params['bottom_bar_quantity'].to_i]
            end
          elsif params['bottom_bar_enabled'] == false
            attributes_to_set << ['BOTTOMBAROPTION', 'NO']
          end

          if params['slab_reinforcement_enabled'] == true
            attributes_to_set << ['SLABREINFOPTION', 'YES']
            if params['slab_reinforcement_type']
              valid_slab_reinf_types = ['#3-BAR', '#4-BAR', '#5-BAR', '#6-BAR', '#7-BAR', '#8-BAR', '#9-BAR', '#10-BAR', '#11-BAR', '#14-BAR', '#18-BAR', '6X6-W2.9XW2.9', '6X6-W1.4XW1.4']
              raise "Invalid slab_reinforcement_type '#{params['slab_reinforcement_type']}'. Must be one of: #{valid_slab_reinf_types.join(', ')}" unless valid_slab_reinf_types.include?(params['slab_reinforcement_type'])
              attributes_to_set << ['SLABREINFTYPE', params['slab_reinforcement_type']]
            end
            attributes_to_set << ['SLABREINFSPACING', params['slab_reinforcement_spacing'].to_f] if params['slab_reinforcement_spacing']
          elsif params['slab_reinforcement_enabled'] == false
            attributes_to_set << ['SLABREINFOPTION', 'NO']
          end
        elsif params['rebar_enabled'] == false
          attributes_to_set << ['REBAROPTION', 'NO']
        end

        # Anchor bolts - Enable/Disable
        if params['anchor_bolts_enabled'] == true
          attributes_to_set << ['ABOLTOPTION', 'YES']
        elsif params['anchor_bolts_enabled'] == false
          attributes_to_set << ['ABOLTOPTION', 'NO']
        end

        # Anchor bolt parameters - can be set independently
        if params['bolt_size']
          valid_bolt_sizes = ['10', '12', '14']
          raise "Invalid bolt_size '#{params['bolt_size']}'. Must be one of: #{valid_bolt_sizes.join(', ')}" unless valid_bolt_sizes.include?(params['bolt_size'])
          attributes_to_set << ['BOLTSIZE', params['bolt_size']]
        end

        if params['bolt_diameter']
          valid_bolt_diameters = ['1/2', '5/8']
          raise "Invalid bolt_diameter '#{params['bolt_diameter']}'. Must be one of: #{valid_bolt_diameters.join(', ')}" unless valid_bolt_diameters.include?(params['bolt_diameter'])
          attributes_to_set << ['BOLTDIA', params['bolt_diameter']]
        end

        if params['washer_type']
          valid_washer_types = ['2x2', '3x3']
          raise "Invalid washer_type '#{params['washer_type']}'. Must be one of: #{valid_washer_types.join(', ')}" unless valid_washer_types.include?(params['washer_type'])
          attributes_to_set << ['WASHER', params['washer_type']]
        end

        attributes_to_set << ['BOLTSPACING_FT', params['bolt_spacing_ft'].to_f] if params['bolt_spacing_ft']
        attributes_to_set << ['SILLWIDTH', params['sill_width'].to_f] if params['sill_width']
        attributes_to_set << ['SILLTHICKNESS', params['sill_thickness'].to_f] if params['sill_thickness']
        attributes_to_set << ['CORNERDIST', params['corner_distance'].to_f] if params['corner_distance']

        # FPSF insulation - Enable/Disable
        if params['fpsf_enabled'] == true
          attributes_to_set << ['FPSFOPTION', 'YES']
        elsif params['fpsf_enabled'] == false
          attributes_to_set << ['FPSFOPTION', 'NO']
        end

        # FPSF insulation parameters - can be set independently
        if params['insulation_type']
          valid_insulation_types = ['Vertical Only', 'Vert. and Horz.', 'None']
          raise "Invalid insulation_type '#{params['insulation_type']}'. Must be one of: #{valid_insulation_types.join(', ')}" unless valid_insulation_types.include?(params['insulation_type'])
          attributes_to_set << ['INSULATION', params['insulation_type']]
        end

        attributes_to_set << ['VINSUL', params['vertical_insulation'].to_f] if params['vertical_insulation']
        attributes_to_set << ['WINSUL', params['wing_insulation'].to_f] if params['wing_insulation']
        attributes_to_set << ['CINSUL', params['corner_insulation'].to_f] if params['corner_insulation']
        attributes_to_set << ['DIMA', params['dim_a'].to_f] if params['dim_a']
        attributes_to_set << ['DIMB', params['dim_b'].to_f] if params['dim_b']
        attributes_to_set << ['DIMC', params['dim_c'].to_f] if params['dim_c']

        # Slab insulation - Enable/Disable
        if params['slab_insulation_enabled'] == true
          attributes_to_set << ['SINSULOPTION', 'YES']
        elsif params['slab_insulation_enabled'] == false
          attributes_to_set << ['SINSULOPTION', 'NO']
        end

        # Slab insulation parameter - can be set independently
        attributes_to_set << ['SINSUL', params['slab_insulation'].to_f] if params['slab_insulation']

        # Subbase - Enable/Disable
        if params['subbase_enabled'] == true
          attributes_to_set << ['SUBBASEOPTION', 'YES']
        elsif params['subbase_enabled'] == false
          attributes_to_set << ['SUBBASEOPTION', 'NO']
        end

        # Subbase parameters - can be set independently
        if params['subbase_depth']
          attributes_to_set << ['SUBBASEDEPTH', params['subbase_depth'].to_f]
        end

        if params['subbase_material']
          valid_subbase_materials = ['Gravel', 'Stone1', 'corrugated_metal']
          raise "Invalid subbase_material '#{params['subbase_material']}'. Must be one of: #{valid_subbase_materials.join(', ')}" unless valid_subbase_materials.include?(params['subbase_material'])
          attributes_to_set << ['SUBBASEMAT', params['subbase_material']]
        end

        # Drain - Enable/Disable
        if params['drain_enabled'] == true
          attributes_to_set << ['DRAINOPTION', 'YES']
        elsif params['drain_enabled'] == false
          attributes_to_set << ['DRAINOPTION', 'NO']
        end

        raise "No parameters to modify" if attributes_to_set.empty?

        SU_MCP.log "[SU_MCP] Modifying #{attributes_to_set.length} attributes"

        # Set all attributes with regen=false except the last one
        attributes_to_set.each_with_index do |(attr_name, attr_value), index|
          is_last = (index == attributes_to_set.length - 1)
          SU_MCP.log "[SU_MCP]   Setting #{attr_name} = #{attr_value} (regen: #{is_last})"
          medeek.sog_set_attribute(attr_name, attr_value, foundation_group, is_last)
        end

        SU_MCP.model.commit_operation

        {
          status: 'modified',
          engine: 'medeek',
          foundation_type: 'slab-on-grade',
          group_name: foundation_group.name,
          attributes_modified: attributes_to_set.length,
          message: "Modified foundation '#{foundation_group.name}' - updated #{attributes_to_set.length} parameter(s)"
        }

      rescue => e
        SU_MCP.model.abort_operation

        if e.message.include?("license") || e.message.include?("License")
          raise "Medeek Foundation Plugin license required. Please activate your license in SketchUp."
        else
          raise "Medeek Foundation Plugin error: #{e.message}"
        end
      end
    end

    # Get foundation information including critical slab_top_z value
    # The input Z coordinate IS the slab top - no calculation needed
    def self.get_info(params = {})
      group_name = params['group_name']

      # Find foundation group
      if group_name
        foundation_group = SU_MCP.model.entities.grep(Sketchup::Group).find do |g|
          g.name == group_name
        end
        raise "Foundation '#{group_name}' not found" unless foundation_group
      else
        # Find any foundation group
        foundation_group = SU_MCP.model.entities.grep(Sketchup::Group).find do |g|
          g.name =~ /FOUNDATION_SOG_POLYGON_ASSEMBLY/
        end
        raise "No foundation found in model. Please specify group_name or create a foundation first." unless foundation_group
      end

      # Read Medeek attributes
      attrs = foundation_group.attribute_dictionaries
      unless attrs && attrs["medeek_foundation_param"]
        raise "Foundation group does not have Medeek Foundation attributes"
      end

      param_dict = attrs["medeek_foundation_param"]

      # The input Z coordinate IS the slab top
      pt0 = param_dict["PT0"]
      slab_top_z = pt0.z.to_f

      # Get outline points
      point_count = param_dict["POINTCOUNT"].to_i
      outline_points = []
      (0...point_count).each do |i|
        pt = param_dict["PT#{i}"]
        outline_points << [pt.x.to_f, pt.y.to_f, pt.z.to_f] if pt
      end

      # Get other info
      slab_thickness = param_dict["SLABTHICKNESS"]
      foundation_depth = param_dict["FDEPTH"]
      footing_width = param_dict["FTGWIDTH"]

      rebar_dict = attrs["medeek_foundation_rebar"]
      rebar_enabled = rebar_dict && rebar_dict["REBAROPTION"] == "YES"

      anchor_bolts_enabled = param_dict["ABOLTOPTION"] == "YES"

      {
        status: 'success',
        group_name: foundation_group.name,
        foundation_type: 'slab-on-grade',
        slab_top_z: slab_top_z,
        slab_thickness: slab_thickness,
        foundation_depth: foundation_depth,
        footing_width: footing_width,
        outline_points: outline_points,
        rebar_enabled: rebar_enabled,
        anchor_bolts_enabled: anchor_bolts_enabled,
        message: "Foundation '#{foundation_group.name}': slab top at Z=#{slab_top_z.round(2)}\", use this Z value for wall placement"
      }
    end

    private

    # Tag slab entities with "Slab" layer for organization
    # Medeek Foundation Plugin organizes components in named groups
    def self.tag_slab_entities(foundation_group, slab_thickness, origin_z)
      # Create or get the tags/layers
      slab_tag = SU_MCP.model.layers.add("Slab")
      rebar_tag = SU_MCP.model.layers.add("foundation rebar")

      slab_count = 0
      rebar_count = 0

      # Iterate through all nested groups in the foundation
      foundation_group.entities.grep(Sketchup::Group).each do |group|
        name = group.name

        # Tag the SLAB_ON_GRADE group (concrete slab geometry)
        if name == "SLAB_ON_GRADE"
          group.layer = slab_tag
          slab_count += 1

        # Tag rebar components:
        # - REBAR * (top/bottom footing bars)
        # - TRANS * (transition/dowel bars)
        # - LONG * (longitudinal slab reinforcement)
        elsif name =~ /^REBAR\s|^TRANS\s|^LONG\s/
          group.layer = rebar_tag
          rebar_count += 1
        end
      end

      SU_MCP.log "[SU_MCP] Tagged #{slab_count} slab group(s) with 'Slab' layer"
      SU_MCP.log "[SU_MCP] Tagged #{rebar_count} rebar group(s) with 'foundation rebar' layer"

      slab_count + rebar_count
    end

    # Calculate perimeter length from points array
    def self.calculate_perimeter(pts)
      perimeter = 0.0
      pts.each_with_index do |pt, i|
        next_pt = pts[(i + 1) % pts.length]
        p1 = Geom::Point3d.new(pt)
        p2 = Geom::Point3d.new(next_pt)
        perimeter += p1.distance(p2)
      end
      perimeter
    end
  end
end
