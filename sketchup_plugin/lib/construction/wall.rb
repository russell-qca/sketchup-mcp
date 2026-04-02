# frozen_string_literal: true

module Construction
  # Wall - Creates framed walls with studs, plates, and openings
  # Supports standard 16" or 24" OC framing with proper headers and rough openings
  class Wall
    # Create a framed wall with studs, plates, and optional openings
    def self.create(params = {})
      length_ft = params['length'].to_f
      length = length_ft * 12.0  # Convert to inches
      height_ft = params['height'] || 8.0
      height = height_ft.to_f * 12.0  # Convert to inches

      stud_spacing = params['stud_spacing'] || 16.0  # inches OC
      lumber_size = params['lumber_size'] || '2x4'
      origin_arr = params['origin']
      openings = params['openings'] || []

      # Parse lumber dimensions
      lumber_dims = case lumber_size
                    when '2x4' then [1.5, 3.5]
                    when '2x6' then [1.5, 5.5]
                    when '2x8' then [1.5, 7.25]
                    else [1.5, 3.5]
                    end
      lumber_width, lumber_depth = lumber_dims

      # Origin point (left end of bottom plate)
      origin = origin_arr ? SU_MCP.parse_point(origin_arr) : SU_MCP::ORIGIN

      raise "Length must be positive" if length <= 0
      raise "Height must be positive" if height <= 0

      SU_MCP.model.start_operation('MCP Create Wall', true)

      # Create wall group
      group = SU_MCP.entities.add_group
      ents = group.entities

      # COORDINATE SYSTEM:
      # X-axis: along wall length (left to right)
      # Y-axis: wall thickness (away from viewer)
      # Z-axis: wall height (up)
      # Wall created from origin, extends in +X and +Z

      # ===== BOTTOM PLATE =====
      create_plate(ents, origin.x, origin.y, origin.z, length, lumber_width, lumber_depth)

      # ===== TOP PLATES (DOUBLE) =====
      top_z = origin.z + height - (2 * lumber_depth)  # Bottom of top plates
      create_plate(ents, origin.x, origin.y, top_z, length, lumber_width, lumber_depth)
      create_plate(ents, origin.x, origin.y, top_z + lumber_depth, length, lumber_width, lumber_depth)

      # ===== STUDS =====
      # Calculate stud positions
      stud_positions = calculate_stud_positions(length, stud_spacing, openings)

      # Stud height: from top of bottom plate to bottom of bottom top plate
      stud_bottom_z = origin.z + lumber_depth
      stud_top_z = top_z
      stud_height = stud_top_z - stud_bottom_z

      # Create studs at calculated positions
      stud_positions.each do |x_pos|
        create_stud(ents, origin.x + x_pos, origin.y, stud_bottom_z, stud_height, lumber_width, lumber_depth)
      end

      # ===== OPENINGS (DOORS/WINDOWS) =====
      openings.each do |opening|
        create_opening_framing(
          ents,
          opening,
          origin,
          stud_bottom_z,
          stud_top_z,
          lumber_width,
          lumber_depth
        )
      end

      SU_MCP.model.commit_operation

      group.name = "Wall_#{length_ft.to_i}ft_#{height_ft.to_i}ft"

      {
        status: 'created',
        length_ft: length_ft,
        height_ft: height_ft,
        stud_spacing: stud_spacing,
        lumber_size: lumber_size,
        stud_count: stud_positions.length,
        opening_count: openings.length,
        entity_id: group.entityID
      }
    end

    private

    # Create a horizontal plate (bottom or top plate)
    def self.create_plate(ents, x, y, z, length, lumber_width, lumber_depth)
      # Plate runs along X-axis, thickness in Y, depth in Z
      pts = [
        Geom::Point3d.new(x, y, z),
        Geom::Point3d.new(x + length, y, z),
        Geom::Point3d.new(x + length, y, z + lumber_depth),
        Geom::Point3d.new(x, y, z + lumber_depth)
      ]
      face = ents.add_face(pts)
      face.pushpull(lumber_width) if face
    end

    # Create a vertical stud
    def self.create_stud(ents, x, y, z_bottom, height, lumber_width, lumber_depth)
      # Stud centered at x position, extends in Z
      half_depth = lumber_depth / 2.0

      pts = [
        Geom::Point3d.new(x - half_depth, y, z_bottom),
        Geom::Point3d.new(x + half_depth, y, z_bottom),
        Geom::Point3d.new(x + half_depth, y, z_bottom + height),
        Geom::Point3d.new(x - half_depth, y, z_bottom + height)
      ]
      face = ents.add_face(pts)
      face.pushpull(lumber_width) if face
    end

    # Calculate where studs should be placed, accounting for openings
    def self.calculate_stud_positions(length, spacing, openings)
      positions = []

      # Start with corner studs
      positions << 0  # Left corner
      positions << length  # Right corner

      # Add studs at regular spacing
      # Start from left corner, go until we reach right corner
      current = spacing
      while current < length
        # Check if this position conflicts with an opening
        conflicts = false
        openings.each do |opening|
          opening_center = opening['position'].to_f * 12.0  # Convert feet to inches
          opening_width = opening['width'].to_f * 12.0
          opening_left = opening_center - (opening_width / 2.0)
          opening_right = opening_center + (opening_width / 2.0)

          # Skip studs that would be inside the opening
          # (we'll add king/jack studs separately)
          if current > opening_left && current < opening_right
            conflicts = true
            break
          end
        end

        positions << current unless conflicts
        current += spacing
      end

      positions.sort.uniq
    end

    # Create framing around an opening (door or window)
    def self.create_opening_framing(ents, opening, origin, stud_bottom_z, stud_top_z, lumber_width, lumber_depth)
      # Parse opening parameters
      opening_type = opening['type']  # 'door' or 'window'
      position_ft = opening['position'].to_f
      width_ft = opening['width'].to_f
      height_ft = opening['height'].to_f

      # Convert to inches
      opening_center_x = position_ft * 12.0
      opening_width = width_ft * 12.0
      opening_height = height_ft * 12.0

      # Calculate opening boundaries
      opening_left = origin.x + opening_center_x - (opening_width / 2.0)
      opening_right = origin.x + opening_center_x + (opening_width / 2.0)

      # For doors: opening goes to floor
      # For windows: opening has a sill height
      sill_height = opening_type == 'window' ? 36.0 : 0.0  # 36" standard window sill

      opening_bottom_z = origin.z + lumber_depth + sill_height
      opening_top_z = opening_bottom_z + opening_height

      # ===== KING STUDS (full height on each side) =====
      stud_height = stud_top_z - stud_bottom_z
      create_stud(ents, opening_left, origin.y, stud_bottom_z, stud_height, lumber_width, lumber_depth)
      create_stud(ents, opening_right, origin.y, stud_bottom_z, stud_height, lumber_width, lumber_depth)

      # ===== JACK STUDS (trimmers - support header) =====
      # Height from bottom of stud to bottom of header
      jack_height = opening_top_z - stud_bottom_z
      create_stud(ents, opening_left + lumber_depth, origin.y, stud_bottom_z, jack_height, lumber_width, lumber_depth)
      create_stud(ents, opening_right - lumber_depth, origin.y, stud_bottom_z, jack_height, lumber_width, lumber_depth)

      # ===== HEADER =====
      # Size header based on opening width (simplified - real code would use span tables)
      header_depth = opening_width <= 48.0 ? 7.25 : 11.25  # 2x8 or 2x12
      header_z = opening_top_z

      # Header spans from king stud to king stud
      header_length = opening_right - opening_left
      pts = [
        Geom::Point3d.new(opening_left, origin.y, header_z),
        Geom::Point3d.new(opening_right, origin.y, header_z),
        Geom::Point3d.new(opening_right, origin.y, header_z + header_depth),
        Geom::Point3d.new(opening_left, origin.y, header_z + header_depth)
      ]
      face = ents.add_face(pts)
      face.pushpull(lumber_width) if face

      # ===== CRIPPLE STUDS ABOVE HEADER =====
      # Short studs from top of header to bottom of top plate
      cripple_bottom_z = header_z + header_depth
      cripple_height = stud_top_z - cripple_bottom_z

      if cripple_height > 6.0  # Only add if tall enough (> 6 inches)
        # Add cripples at 16" spacing above header
        cripple_x = opening_left + 16.0
        while cripple_x < opening_right - lumber_depth
          create_stud(ents, cripple_x, origin.y, cripple_bottom_z, cripple_height, lumber_width, lumber_depth)
          cripple_x += 16.0
        end
      end

      # ===== SILL AND CRIPPLE STUDS BELOW (for windows only) =====
      if opening_type == 'window' && sill_height > 0
        # Sill (horizontal member at bottom of window)
        sill_z = opening_bottom_z - lumber_depth
        pts = [
          Geom::Point3d.new(opening_left, origin.y, sill_z),
          Geom::Point3d.new(opening_right, origin.y, sill_z),
          Geom::Point3d.new(opening_right, origin.y, sill_z + lumber_depth),
          Geom::Point3d.new(opening_left, origin.y, sill_z + lumber_depth)
        ]
        face = ents.add_face(pts)
        face.pushpull(lumber_width) if face

        # Cripple studs below sill
        cripple_height_below = sill_z - stud_bottom_z
        if cripple_height_below > 6.0
          cripple_x = opening_left + 16.0
          while cripple_x < opening_right - lumber_depth
            create_stud(ents, cripple_x, origin.y, stud_bottom_z, cripple_height_below, lumber_width, lumber_depth)
            cripple_x += 16.0
          end
        end
      end
    end
  end
end
