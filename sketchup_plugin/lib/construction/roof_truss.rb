# frozen_string_literal: true

module Construction
  # RoofTruss - Handles all roof truss construction functionality
  # Supports King Post, Fink (W-truss), and Queen Post truss types
  class RoofTruss
    # Create roof trusses based on parameters
    def self.create(params = {})
      span_ft = params['span'].to_f
      span = span_ft * 12.0  # Convert feet to inches
      pitch = params['pitch'] || "6:12"
      truss_type = params['type'] || 'fink'
      origin_arr = params['origin']
      spacing = params['spacing'] ? params['spacing'].to_f : 24.0  # inches OC
      count = params['count'] ? params['count'].to_i : 1
      lumber_size = params['lumber_size'] || '2x4'
      overhang = params['overhang'] ? params['overhang'].to_f : 12.0  # inches, default 12"

      # Parse lumber dimensions
      lumber_dims = case lumber_size
                    when '2x4' then [1.5, 3.5]
                    when '2x6' then [1.5, 5.5]
                    when '2x8' then [1.5, 7.25]
                    else [1.5, 3.5]
                    end
      lumber_width, lumber_depth = lumber_dims

      # Parse pitch
      rise, run = parse_pitch(pitch)

      # Origin point (left wall location)
      origin = origin_arr ? SU_MCP.parse_point(origin_arr) : SU_MCP::ORIGIN

      raise "Span must be positive" if span <= 0
      raise "Invalid truss type" unless ['king', 'fink'].include?(truss_type)
      raise "Count must be at least 1" if count < 1

      SU_MCP.model.start_operation('MCP Create Roof Trusses', true)

      trusses = []

      count.times do |i|
        # Calculate position for this truss (spaced along Y axis)
        # Trusses extend from Y=0 (front) to Y=-lumber_width (back)
        # For the last truss: offset forward by lumber_width so back face is flush with building end
        # (All other trusses use front face as reference)
        offset_adjustment = (i == count - 1) ? lumber_width : 0
        truss_origin = origin.offset(SU_MCP::Y_AXIS, i * spacing + offset_adjustment)

        # Create truss based on type using accurate functions
        truss = case truss_type
                when 'king'
                  create_king_post_truss_accurate(span, rise, run, overhang, truss_origin, lumber_width, lumber_depth)
                when 'fink'
                  create_fink_truss_accurate(span, rise, run, overhang, truss_origin, lumber_width, lumber_depth)
                end

        SU_MCP.apply_layer(truss, params['layer']) if params['layer']
        trusses << truss.entityID if truss
      end

      SU_MCP.model.commit_operation

      {
        status: 'created',
        truss_type: truss_type,
        count: count,
        span_ft: span_ft,
        pitch: pitch,
        spacing: spacing,
        overhang: overhang,
        lumber_size: lumber_size,
        truss_ids: trusses
      }
    end

    private

    # Parse pitch like "6:12" or "6/12" into rise/run ratio
    def self.parse_pitch(pitch_str)
      parts = pitch_str.to_s.split(/[:\/]/)
      rise = parts[0].to_f
      run = parts.length > 1 ? parts[1].to_f : 12.0
      [rise, run]
    end

    # Create a lumber member (like 2x4) along a slope
    def self.create_lumber_member_sloped(ents, pt_bottom_start, pt_bottom_end, lumber_width, lumber_depth, trim_start: false, trim_end: false)
      # pt_bottom_start, pt_bottom_end: bottom edge endpoints
      # lumber_depth: perpendicular to slope (3.5" for 2x4)
      # lumber_width: extrusion thickness (1.5" for 2x4)
      # trim_start: if true, trim with vertical cut at start (for apex joints)
      # trim_end: if true, trim with vertical cut at end (for apex joints)
      # COORDINATE SYSTEM: All members at Y=0 plane, extruded to Y=-lumber_width

      # Calculate slope angle
      dx = pt_bottom_end.x - pt_bottom_start.x
      dz = pt_bottom_end.z - pt_bottom_start.z
      angle = Math.atan2(dz, dx)

      # Offset perpendicular to slope for top edge
      offset_x = -lumber_depth * Math.sin(angle)
      offset_z = lumber_depth * Math.cos(angle)

      # Four corners of the profile at Y=0
      pt_bottom_start_y0 = Geom::Point3d.new(pt_bottom_start.x, 0, pt_bottom_start.z)
      pt_bottom_end_y0 = Geom::Point3d.new(pt_bottom_end.x, 0, pt_bottom_end.z)
      pt_top_start_y0 = Geom::Point3d.new(
        pt_bottom_start.x + offset_x,
        0,
        pt_bottom_start.z + offset_z
      )
      pt_top_end_y0 = Geom::Point3d.new(
        pt_bottom_end.x + offset_x,
        0,
        pt_bottom_end.z + offset_z
      )

      # Apply vertical trims at ends if requested (for apex/heel joints)
      # Trim adjusts points to create vertical cut face
      if trim_end
        # Trim end: move bottom_end to align with top_end X coordinate (for vertical cut)
        pt_bottom_end_y0 = Geom::Point3d.new(pt_top_end_y0.x, 0, pt_bottom_end.z)
      end

      if trim_start
        # Trim start: move bottom_start to align with top_start X coordinate (for vertical cut)
        pt_bottom_start_y0 = Geom::Point3d.new(pt_top_start_y0.x, 0, pt_bottom_start.z)
      end

      # Create face at Y=0 and extrude in -Y direction (Y=0 to Y=-lumber_width)
      face = ents.add_face([pt_bottom_start_y0, pt_bottom_end_y0, pt_top_end_y0, pt_top_start_y0])
      face.pushpull(-lumber_width) if face  # Negative: Y=0 to Y=-lumber_width
      face
    end

    # Create a vertical lumber member (like king post)
    def self.create_lumber_member_vertical(ents, x, z_bottom, z_top, lumber_width, lumber_depth)
      # Centered at x position
      # Using EXACT same pattern as bottom chord for consistency
      half_depth = lumber_depth / 2.0

      x_left = x - half_depth
      x_right = x + half_depth

      # Create profile at Y=0 with same point ordering as bottom chord
      face = ents.add_face(
        Geom::Point3d.new(x_left, 0, z_bottom),
        Geom::Point3d.new(x_right, 0, z_bottom),
        Geom::Point3d.new(x_right, 0, z_top),
        Geom::Point3d.new(x_left, 0, z_top)
      )

      # Extrude in positive Y direction (same as bottom chord)
      face.pushpull(lumber_width) if face
      face
    end

    # Accurate King Post truss based on professional truss geometry analysis
    def self.create_king_post_truss_accurate(span, rise, run, overhang, origin, lumber_width, lumber_depth)
      # All dimensions in inches
      #
      # COORDINATE SYSTEM:
      # X-Z plane: origin.z = base of bottom chord, bc_top_z = top of bottom chord
      # Y plane: All members created at Y=0, extruded to Y=-lumber_width (-1.5" for 2x4)
      # This ensures all members are coplanar from Y=-lumber_width to Y=0

      run_to_peak = span / 2.0
      rise_to_peak = (run_to_peak / run) * rise
      bc_top_z = origin.z + lumber_depth  # Top of bottom chord is the reference plane

      # Create truss group
      group = SU_MCP.entities.add_group
      ents = group.entities

      # Bottom Chord - horizontal, EXACTLY span length (no overhang)
      # Ends cut at pitch angle for proper heel joint
      # COORDINATE SYSTEM: Y=0 plane, extruded to Y=-lumber_width

      # Calculate horizontal distance for angled cut based on pitch
      # For pitch rise:run, to cover lumber_depth vertically: horizontal = lumber_depth * (run/rise)
      cut_horizontal = lumber_depth * (run / rise)

      bc_start_x = origin.x
      bc_end_x = origin.x + span

      # Profile with angled cuts at both ends
      pts = [
        Geom::Point3d.new(bc_start_x, 0, origin.z),                      # Bottom-left corner
        Geom::Point3d.new(bc_end_x, 0, origin.z),                        # Bottom-right corner
        Geom::Point3d.new(bc_end_x - cut_horizontal, 0, bc_top_z),      # Top-right (cut inward)
        Geom::Point3d.new(bc_start_x + cut_horizontal, 0, bc_top_z)     # Top-left (cut inward)
      ]
      face = ents.add_face(pts)
      face.pushpull(-lumber_width) if face  # Negative: Y=0 to Y=-lumber_width

      # Top Chord heel and peak positions (bottom edge of top chord members)
      #
      # *** ABSOLUTE REQUIREMENT - DO NOT CHANGE ***
      # The heel joint intersection is FIXED:
      # - Bottom left corner of BC = Bottom start of left TC = (origin.x, origin.z)
      # - Bottom right corner of BC = Bottom end of right TC = (origin.x + span, origin.z)
      # Any future overhang calculations extend BEYOND these fixed points
      #
      heel_left_x = origin.x
      heel_left_z = origin.z

      heel_right_x = origin.x + span
      heel_right_z = origin.z

      # Peak: at center, measured from BOTTOM of bottom chord (DO NOT CHANGE)
      # For 24' span, 6:12 pitch: rise = 72", so peak_z = origin.z + 72"
      peak_x = origin.x + run_to_peak
      peak_z = origin.z + rise_to_peak

      # Left top chord - WITH overhang extension and vertical cuts
      # Overhang measured horizontally from heel joint to outer edge
      # Bottom edge drops according to pitch: (overhang / run) * rise
      left_dx = peak_x - heel_left_x
      left_dz = peak_z - heel_left_z
      left_angle = Math.atan2(left_dz, left_dx)
      left_offset_z = lumber_depth * Math.cos(left_angle)

      # Outer edge position (with overhang)
      tc_left_outer_x = heel_left_x - overhang
      tc_left_outer_z = heel_left_z - (overhang / run) * rise

      # Four corners: outer edge (left) to apex (right), with vertical cuts at both ends
      # NOTE: TC still passes through absolute heel joint (heel_left_x, heel_left_z)
      tc_left_bottom_left = Geom::Point3d.new(tc_left_outer_x, 0, tc_left_outer_z)
      tc_left_top_left = Geom::Point3d.new(tc_left_outer_x, 0, tc_left_outer_z + lumber_depth / Math.cos(left_angle))
      tc_left_top_right = Geom::Point3d.new(peak_x, 0, peak_z + left_offset_z)
      tc_left_bottom_right = Geom::Point3d.new(peak_x, 0, peak_z)

      tc_left_face = ents.add_face([tc_left_bottom_left, tc_left_bottom_right, tc_left_top_right, tc_left_top_left])
      tc_left_face.pushpull(-lumber_width) if tc_left_face

      # Right top chord - WITH overhang extension and vertical cuts
      # Overhang measured horizontally from heel joint to outer edge
      # Bottom edge drops according to pitch: (overhang / run) * rise
      right_dx = heel_right_x - peak_x
      right_dz = heel_right_z - peak_z
      right_angle = Math.atan2(right_dz, right_dx)
      right_offset_z = lumber_depth * Math.cos(right_angle)

      # Outer edge position (with overhang)
      tc_right_outer_x = heel_right_x + overhang
      tc_right_outer_z = heel_right_z - (overhang / run) * rise

      # Four corners: apex (left) to outer edge (right), with vertical cuts at both ends
      # NOTE: TC still passes through absolute heel joint (heel_right_x, heel_right_z)
      tc_right_bottom_left = Geom::Point3d.new(peak_x, 0, peak_z)
      tc_right_top_left = Geom::Point3d.new(peak_x, 0, peak_z + right_offset_z)
      tc_right_top_right = Geom::Point3d.new(tc_right_outer_x, 0, tc_right_outer_z + lumber_depth / Math.cos(right_angle))
      tc_right_bottom_right = Geom::Point3d.new(tc_right_outer_x, 0, tc_right_outer_z)

      tc_right_face = ents.add_face([tc_right_bottom_left, tc_right_bottom_right, tc_right_top_right, tc_right_top_left])
      tc_right_face.pushpull(-lumber_width) if tc_right_face

      # King Post - vertical member at center, from BC top to peak
      # Top has peaked cuts matching slope of top chords
      # COORDINATE SYSTEM: Y=0 plane, extruded to Y=-lumber_width (same as all members)
      kp_x = origin.x + run_to_peak
      kp_z_bottom = bc_top_z

      half_depth = lumber_depth / 2.0
      kp_left = kp_x - half_depth
      kp_right = kp_x + half_depth

      # Top of king post: peaked with angled cuts parallel to TC bottom edges
      # At center peak: (peak_x, peak_z)
      # Moving left/right by half_depth, drop according to roof pitch
      kp_top_drop = half_depth * (rise / run)

      # Create pentagonal profile: bottom left, bottom right, top right, peak, top left
      kp_face = ents.add_face(
        Geom::Point3d.new(kp_left, 0, kp_z_bottom),           # Bottom left
        Geom::Point3d.new(kp_right, 0, kp_z_bottom),          # Bottom right
        Geom::Point3d.new(kp_right, 0, peak_z - kp_top_drop), # Top right (angled cut)
        Geom::Point3d.new(peak_x, 0, peak_z),                 # Peak center
        Geom::Point3d.new(kp_left, 0, peak_z - kp_top_drop)   # Top left (angled cut)
      )
      kp_face.pushpull(-lumber_width) if kp_face  # Negative: Y=0 to Y=-lumber_width

      # Add the end cap face at Y=0 (pushpull consumes the original face)
      ents.add_face(
        Geom::Point3d.new(kp_left, 0, kp_z_bottom),           # Bottom left
        Geom::Point3d.new(kp_right, 0, kp_z_bottom),          # Bottom right
        Geom::Point3d.new(kp_right, 0, peak_z - kp_top_drop), # Top right (angled cut)
        Geom::Point3d.new(peak_x, 0, peak_z),                 # Peak center
        Geom::Point3d.new(kp_left, 0, peak_z - kp_top_drop)   # Top left (angled cut)
      )

      group.name = "King_Post_Truss_#{span.to_i}ft_#{rise.to_i}-#{run.to_i}"
      group
    end

    # Fink (W-truss) implementation based on formal engineering specification
    # See: resources/fink_truss_engineering_spec.md
    def self.create_fink_truss_accurate(span, rise, run, overhang, origin, lumber_width, lumber_depth)
      # COORDINATE SYSTEM:
      # X-Z plane: origin.z = base of bottom chord, bc_top_z = top of bottom chord
      # Y plane: All members created at Y=0, extruded to Y=-lumber_width (-1.5" for 2x4)
      # This ensures all members are coplanar from Y=-lumber_width to Y=0

      run_to_peak = span / 2.0
      rise_to_peak = (run_to_peak / run) * rise
      bc_top_z = origin.z + lumber_depth  # Top of bottom chord is the reference plane

      group = SU_MCP.entities.add_group
      ents = group.entities

      # ===== BOTTOM CHORD =====
      # EXACTLY span length (no overhang), ends cut at pitch angle
      # COORDINATE SYSTEM: Y=0 plane, extruded to Y=-lumber_width

      # Calculate horizontal distance for angled cut based on pitch
      cut_horizontal = lumber_depth * (run / rise)

      bc_start_x = origin.x
      bc_end_x = origin.x + span

      # Profile with angled cuts at both ends
      pts = [
        Geom::Point3d.new(bc_start_x, 0, origin.z),                      # Bottom-left corner
        Geom::Point3d.new(bc_end_x, 0, origin.z),                        # Bottom-right corner
        Geom::Point3d.new(bc_end_x - cut_horizontal, 0, bc_top_z),      # Top-right (cut inward)
        Geom::Point3d.new(bc_start_x + cut_horizontal, 0, bc_top_z)     # Top-left (cut inward)
      ]
      face = ents.add_face(pts)
      face.pushpull(-lumber_width) if face  # Negative: Y=0 to Y=-lumber_width

      # ===== TOP CHORD HEEL AND PEAK POSITIONS =====
      #
      # *** ABSOLUTE REQUIREMENT - DO NOT CHANGE ***
      # The heel joint intersection is FIXED:
      # - Bottom left corner of BC = Bottom start of left TC = (origin.x, origin.z)
      # - Bottom right corner of BC = Bottom end of right TC = (origin.x + span, origin.z)
      # Any future overhang calculations extend BEYOND these fixed points
      #
      heel_left_x = origin.x
      heel_left_z = origin.z

      heel_right_x = origin.x + span
      heel_right_z = origin.z

      # Peak: at center, measured from BOTTOM of bottom chord (DO NOT CHANGE)
      peak_x = origin.x + run_to_peak
      peak_z = origin.z + rise_to_peak

      # ===== TOP CHORDS =====
      # Left top chord - WITH overhang extension and vertical cuts
      # Overhang measured horizontally from heel joint to outer edge
      # Bottom edge drops according to pitch: (overhang / run) * rise
      left_dx = peak_x - heel_left_x
      left_dz = peak_z - heel_left_z
      left_angle = Math.atan2(left_dz, left_dx)
      left_offset_z = lumber_depth * Math.cos(left_angle)

      # Outer edge position (with overhang)
      tc_left_outer_x = heel_left_x - overhang
      tc_left_outer_z = heel_left_z - (overhang / run) * rise

      # Four corners: outer edge (left) to apex (right), with vertical cuts at both ends
      # NOTE: TC still passes through absolute heel joint (heel_left_x, heel_left_z)
      tc_left_bottom_left = Geom::Point3d.new(tc_left_outer_x, 0, tc_left_outer_z)
      tc_left_top_left = Geom::Point3d.new(tc_left_outer_x, 0, tc_left_outer_z + lumber_depth / Math.cos(left_angle))
      tc_left_top_right = Geom::Point3d.new(peak_x, 0, peak_z + left_offset_z)
      tc_left_bottom_right = Geom::Point3d.new(peak_x, 0, peak_z)

      tc_left_face = ents.add_face([tc_left_bottom_left, tc_left_bottom_right, tc_left_top_right, tc_left_top_left])
      tc_left_face.pushpull(-lumber_width) if tc_left_face

      # Right top chord - WITH overhang extension and vertical cuts
      # Overhang measured horizontally from heel joint to outer edge
      # Bottom edge drops according to pitch: (overhang / run) * rise
      right_dx = heel_right_x - peak_x
      right_dz = heel_right_z - peak_z
      right_angle = Math.atan2(right_dz, right_dx)
      right_offset_z = lumber_depth * Math.cos(right_angle)

      # Outer edge position (with overhang)
      tc_right_outer_x = heel_right_x + overhang
      tc_right_outer_z = heel_right_z - (overhang / run) * rise

      # Four corners: apex (left) to outer edge (right), with vertical cuts at both ends
      # NOTE: TC still passes through absolute heel joint (heel_right_x, heel_right_z)
      tc_right_bottom_left = Geom::Point3d.new(peak_x, 0, peak_z)
      tc_right_top_left = Geom::Point3d.new(peak_x, 0, peak_z + right_offset_z)
      tc_right_top_right = Geom::Point3d.new(tc_right_outer_x, 0, tc_right_outer_z + lumber_depth / Math.cos(right_angle))
      tc_right_bottom_right = Geom::Point3d.new(tc_right_outer_x, 0, tc_right_outer_z)

      tc_right_face = ents.add_face([tc_right_bottom_left, tc_right_bottom_right, tc_right_top_right, tc_right_top_left])
      tc_right_face.pushpull(-lumber_width) if tc_right_face

      # ===== WEB MEMBERS - FINK W-PATTERN =====
      # Centerlines and parallel offset lines (1.75" on each side in X-Z plane)
      # Divide bottom chord into three equal sections
      panel_1_x = origin.x + (span / 3.0)
      panel_2_x = origin.x + (2.0 * span / 3.0)

      # ----- Left Web -----
      # Calculate perpendicular offset in X-Z plane (1.75" = half of 3.5")
      web_left_dx = peak_x - panel_1_x
      web_left_dz = peak_z - bc_top_z
      web_left_angle = Math.atan2(web_left_dz, web_left_dx)

      offset = 1.75
      web_left_perp_x = -offset * Math.sin(web_left_angle)
      web_left_perp_z = offset * Math.cos(web_left_angle)

      # Parallel line +1.75" perpendicular (outer left) - extend to BC and up to left TC
      # Bottom: Calculate where the offset line intersects bc_top_z
      # The line passes through (panel_1_x + perp_x, bc_top_z + perp_z) with slope tan(angle)
      # To find where it crosses bc_top_z: x = (panel_1_x + perp_x) - perp_z / tan(angle)
      web_left_bottom_plus_x = panel_1_x + web_left_perp_x - web_left_perp_z / Math.tan(web_left_angle)
      web_left_bottom_plus = Geom::Point3d.new(
        web_left_bottom_plus_x,
        0,
        bc_top_z
      )

      # Top: find intersection with left TC bottom edge
      # Web line direction (parallel to centerline)
      web_line_dx = web_left_dx
      web_line_dz = web_left_dz

      # Left TC bottom edge: from (heel_left_x, heel_left_z) to (peak_x, peak_z)
      tc_line_dx = peak_x - heel_left_x
      tc_line_dz = peak_z - heel_left_z

      # Line-line intersection: web line from web_left_bottom_plus, TC line from heel
      # Parametric: web = bottom + t * direction, TC = heel + s * direction
      # bottom.x + t * web_dx = heel.x + s * tc_dx
      # bottom.z + t * web_dz = heel.z + s * tc_dz
      # Solve for t using Cramer's rule
      denominator = web_line_dx * tc_line_dz - web_line_dz * tc_line_dx
      if denominator.abs > 0.001  # Check for parallel lines
        numerator_t = (heel_left_x - web_left_bottom_plus.x) * tc_line_dz - (heel_left_z - bc_top_z) * tc_line_dx
        t = numerator_t / denominator

        # Calculate intersection point
        web_left_top_plus = Geom::Point3d.new(
          web_left_bottom_plus.x + t * web_line_dx,
          0,
          bc_top_z + t * web_line_dz
        )
      else
        # Fallback if lines are parallel (shouldn't happen)
        web_left_top_plus = Geom::Point3d.new(
          peak_x + web_left_perp_x,
          0,
          peak_z + web_left_perp_z
        )
      end
      # Store for later face creation
      web_left_outer_bottom = web_left_bottom_plus

      # Parallel line -1.75" perpendicular (inner left) - extend to BC and intersection
      # Bottom: Calculate where the offset line intersects bc_top_z
      # The line passes through (panel_1_x - perp_x, bc_top_z - perp_z) with slope tan(angle)
      # To find where it crosses bc_top_z: x = (panel_1_x - perp_x) + perp_z / tan(angle)
      web_left_bottom_minus_x = panel_1_x - web_left_perp_x + web_left_perp_z / Math.tan(web_left_angle)
      web_left_bottom_minus = Geom::Point3d.new(
        web_left_bottom_minus_x,
        0,
        bc_top_z
      )
      # Store for later intersection calculation with right inner line
      web_left_inner_bottom = web_left_bottom_minus
      web_left_inner_dir_x = web_left_dx
      web_left_inner_dir_z = web_left_dz

      # ----- Right Web -----
      # Calculate perpendicular offset in X-Z plane
      web_right_dx = peak_x - panel_2_x
      web_right_dz = peak_z - bc_top_z
      web_right_angle = Math.atan2(web_right_dz, web_right_dx)

      web_right_perp_x = -offset * Math.sin(web_right_angle)
      web_right_perp_z = offset * Math.cos(web_right_angle)

      # Parallel line +1.75" perpendicular (inner right) - extend to BC and intersection
      # Bottom: Calculate where the offset line intersects bc_top_z
      # The line passes through (panel_2_x + perp_x, bc_top_z + perp_z) with slope tan(angle)
      # To find where it crosses bc_top_z: x = (panel_2_x + perp_x) - perp_z / tan(angle)
      web_right_bottom_plus_x = panel_2_x + web_right_perp_x - web_right_perp_z / Math.tan(web_right_angle)
      web_right_bottom_plus = Geom::Point3d.new(
        web_right_bottom_plus_x,
        0,
        bc_top_z
      )
      # Store for intersection calculation with left inner line
      web_right_inner_bottom = web_right_bottom_plus
      web_right_inner_dir_x = web_right_dx
      web_right_inner_dir_z = web_right_dz

      # Calculate intersection of inner lines (left -1.75" and right +1.75")
      # Left inner: from web_left_inner_bottom along web_left direction
      # Right inner: from web_right_inner_bottom along web_right direction
      inner_denominator = web_left_inner_dir_x * web_right_inner_dir_z - web_left_inner_dir_z * web_right_inner_dir_x
      if inner_denominator.abs > 0.001
        inner_numerator = (web_right_inner_bottom.x - web_left_inner_bottom.x) * web_right_inner_dir_z - (bc_top_z - bc_top_z) * web_right_inner_dir_x
        t_inner = inner_numerator / inner_denominator

        # Calculate intersection point
        inner_intersection = Geom::Point3d.new(
          web_left_inner_bottom.x + t_inner * web_left_inner_dir_x,
          0,
          bc_top_z + t_inner * web_left_inner_dir_z
        )
      else
        # Fallback if parallel (shouldn't happen)
        inner_intersection = Geom::Point3d.new(peak_x, 0, peak_z)
      end

      # Store left inner top for later
      web_left_inner_top = inner_intersection

      # Parallel line -1.75" perpendicular (outer right) - extend to BC and up to right TC
      # Bottom: Calculate where the offset line intersects bc_top_z
      # The line passes through (panel_2_x - perp_x, bc_top_z - perp_z) with slope tan(angle)
      # To find where it crosses bc_top_z: x = (panel_2_x - perp_x) + perp_z / tan(angle)
      web_right_bottom_minus_x = panel_2_x - web_right_perp_x + web_right_perp_z / Math.tan(web_right_angle)
      web_right_bottom_minus = Geom::Point3d.new(
        web_right_bottom_minus_x,
        0,
        bc_top_z
      )

      # Top: find intersection with right TC bottom edge
      # Web line direction (parallel to centerline)
      web_line_dx_r = web_right_dx
      web_line_dz_r = web_right_dz

      # Right TC bottom edge: from (peak_x, peak_z) to (heel_right_x, heel_right_z)
      tc_line_dx_r = heel_right_x - peak_x
      tc_line_dz_r = heel_right_z - peak_z

      # Line-line intersection
      denominator_r = web_line_dx_r * tc_line_dz_r - web_line_dz_r * tc_line_dx_r
      if denominator_r.abs > 0.001
        numerator_t_r = (peak_x - web_right_bottom_minus.x) * tc_line_dz_r - (peak_z - bc_top_z) * tc_line_dx_r
        t_r = numerator_t_r / denominator_r

        # Calculate intersection point
        web_right_top_minus = Geom::Point3d.new(
          web_right_bottom_minus.x + t_r * web_line_dx_r,
          0,
          bc_top_z + t_r * web_line_dz_r
        )
      else
        # Fallback if lines are parallel
        web_right_top_minus = Geom::Point3d.new(
          peak_x - web_right_perp_x,
          0,
          peak_z - web_right_perp_z
        )
      end
      # Store right outer for later
      web_right_outer_bottom = web_right_bottom_minus
      web_right_outer_top = web_right_top_minus
      web_right_inner_top = inner_intersection

      # Create apex point
      apex_point = Geom::Point3d.new(peak_x, 0, peak_z)

      # Create LEFT WEB as a closed face (5 vertices in order)
      # Start at bottom outer, go counterclockwise
      left_web_vertices = [
        web_left_outer_bottom,      # Bottom left (outer)
        web_left_top_plus,           # Top left (at TC)
        apex_point,                  # Top center (apex)
        web_left_inner_top,          # Top right (inner intersection)
        web_left_inner_bottom        # Bottom right (inner)
      ]
      left_web_face = ents.add_face(left_web_vertices)

      # Create RIGHT WEB as a closed face (5 vertices in order)
      # Reverse the vertex order to match the left web's normal direction
      right_web_vertices = [
        web_right_outer_bottom,      # Bottom right (outer)
        web_right_outer_top,         # Top right (at TC)
        apex_point,                  # Top center (apex)
        web_right_inner_top,         # Top left (inner intersection)
        web_right_inner_bottom       # Bottom left (inner)
      ]
      right_web_face = ents.add_face(right_web_vertices)

      # ===== OUTER WEB MEMBERS =====
      # These go from panel points to midpoints of top chords

      # Calculate midpoint of left top chord (from heel to peak)
      left_tc_mid_x = (heel_left_x + peak_x) / 2.0
      left_tc_mid_z = (heel_left_z + peak_z) / 2.0

      # Calculate midpoint of right top chord (from peak to heel)
      right_tc_mid_x = (peak_x + heel_right_x) / 2.0
      right_tc_mid_z = (peak_z + heel_right_z) / 2.0

      # ----- Left Outer Web -----
      # Calculate perpendicular offset in X-Z plane (1.75" = half of 3.5")
      left_outer_dx = left_tc_mid_x - panel_1_x
      left_outer_dz = left_tc_mid_z - bc_top_z
      left_outer_angle = Math.atan2(left_outer_dz, left_outer_dx)

      left_outer_perp_x = -offset * Math.sin(left_outer_angle)
      left_outer_perp_z = offset * Math.cos(left_outer_angle)

      # Left TC bottom surface line: from (heel_left_x, heel_left_z) to (peak_x, peak_z)
      left_tc_bottom_dx = peak_x - heel_left_x
      left_tc_bottom_dz = peak_z - heel_left_z

      # Parallel line +1.75" perpendicular (outer side)
      # Bottom: where offset line crosses bc_top_z
      left_outer_bottom_plus_x = panel_1_x + left_outer_perp_x - left_outer_perp_z / Math.tan(left_outer_angle)
      left_outer_bottom_plus = Geom::Point3d.new(left_outer_bottom_plus_x, 0, bc_top_z)
      # Top: where offset line intersects left TC bottom surface
      # Line intersection: outer web line vs TC bottom line
      outer_plus_denom = left_outer_dx * left_tc_bottom_dz - left_outer_dz * left_tc_bottom_dx
      if outer_plus_denom.abs > 0.001
        outer_plus_num = (heel_left_x - left_outer_bottom_plus_x) * left_tc_bottom_dz - (heel_left_z - bc_top_z) * left_tc_bottom_dx
        t_outer_plus = outer_plus_num / outer_plus_denom
        left_outer_top_plus = Geom::Point3d.new(
          left_outer_bottom_plus_x + t_outer_plus * left_outer_dx,
          0,
          bc_top_z + t_outer_plus * left_outer_dz
        )
      else
        # Fallback
        left_outer_top_plus = Geom::Point3d.new(left_tc_mid_x + left_outer_perp_x, 0, left_tc_mid_z + left_outer_perp_z)
      end
      # Parallel line -1.75" perpendicular (inner side)
      # Bottom: where offset line crosses bc_top_z
      left_outer_bottom_minus_x = panel_1_x - left_outer_perp_x + left_outer_perp_z / Math.tan(left_outer_angle)
      left_outer_bottom_minus = Geom::Point3d.new(left_outer_bottom_minus_x, 0, bc_top_z)
      # Top: where offset line intersects left TC bottom surface
      outer_minus_denom = left_outer_dx * left_tc_bottom_dz - left_outer_dz * left_tc_bottom_dx
      if outer_minus_denom.abs > 0.001
        outer_minus_num = (heel_left_x - left_outer_bottom_minus_x) * left_tc_bottom_dz - (heel_left_z - bc_top_z) * left_tc_bottom_dx
        t_outer_minus = outer_minus_num / outer_minus_denom
        left_outer_top_minus = Geom::Point3d.new(
          left_outer_bottom_minus_x + t_outer_minus * left_outer_dx,
          0,
          bc_top_z + t_outer_minus * left_outer_dz
        )
      else
        # Fallback
        left_outer_top_minus = Geom::Point3d.new(left_tc_mid_x - left_outer_perp_x, 0, left_tc_mid_z - left_outer_perp_z)
      end

      # Create left outer web as a closed face (4 vertices)
      left_outer_web_vertices = [
        left_outer_bottom_minus,    # Bottom inner
        left_outer_top_minus,       # Top inner
        left_outer_top_plus,        # Top outer
        left_outer_bottom_plus      # Bottom outer
      ]
      left_outer_web_face = ents.add_face(left_outer_web_vertices)

      # ----- Right Outer Web -----
      # Calculate perpendicular offset in X-Z plane
      right_outer_dx = right_tc_mid_x - panel_2_x
      right_outer_dz = right_tc_mid_z - bc_top_z
      right_outer_angle = Math.atan2(right_outer_dz, right_outer_dx)

      right_outer_perp_x = -offset * Math.sin(right_outer_angle)
      right_outer_perp_z = offset * Math.cos(right_outer_angle)

      # Right TC bottom surface line: from (peak_x, peak_z) to (heel_right_x, heel_right_z)
      right_tc_bottom_dx = heel_right_x - peak_x
      right_tc_bottom_dz = heel_right_z - peak_z

      # Parallel line +1.75" perpendicular (inner side)
      # Bottom: where offset line crosses bc_top_z
      right_outer_bottom_plus_x = panel_2_x + right_outer_perp_x - right_outer_perp_z / Math.tan(right_outer_angle)
      right_outer_bottom_plus = Geom::Point3d.new(right_outer_bottom_plus_x, 0, bc_top_z)
      # Top: where offset line intersects right TC bottom surface
      # Line intersection: outer web line vs TC bottom line
      outer_plus_denom_r = right_outer_dx * right_tc_bottom_dz - right_outer_dz * right_tc_bottom_dx
      if outer_plus_denom_r.abs > 0.001
        outer_plus_num_r = (peak_x - right_outer_bottom_plus_x) * right_tc_bottom_dz - (peak_z - bc_top_z) * right_tc_bottom_dx
        t_outer_plus_r = outer_plus_num_r / outer_plus_denom_r
        right_outer_top_plus = Geom::Point3d.new(
          right_outer_bottom_plus_x + t_outer_plus_r * right_outer_dx,
          0,
          bc_top_z + t_outer_plus_r * right_outer_dz
        )
      else
        # Fallback
        right_outer_top_plus = Geom::Point3d.new(right_tc_mid_x + right_outer_perp_x, 0, right_tc_mid_z + right_outer_perp_z)
      end
      # Parallel line -1.75" perpendicular (outer side)
      # Bottom: where offset line crosses bc_top_z
      right_outer_bottom_minus_x = panel_2_x - right_outer_perp_x + right_outer_perp_z / Math.tan(right_outer_angle)
      right_outer_bottom_minus = Geom::Point3d.new(right_outer_bottom_minus_x, 0, bc_top_z)
      # Top: where offset line intersects right TC bottom surface
      outer_minus_denom_r = right_outer_dx * right_tc_bottom_dz - right_outer_dz * right_tc_bottom_dx
      if outer_minus_denom_r.abs > 0.001
        outer_minus_num_r = (peak_x - right_outer_bottom_minus_x) * right_tc_bottom_dz - (peak_z - bc_top_z) * right_tc_bottom_dx
        t_outer_minus_r = outer_minus_num_r / outer_minus_denom_r
        right_outer_top_minus = Geom::Point3d.new(
          right_outer_bottom_minus_x + t_outer_minus_r * right_outer_dx,
          0,
          bc_top_z + t_outer_minus_r * right_outer_dz
        )
      else
        # Fallback
        right_outer_top_minus = Geom::Point3d.new(right_tc_mid_x - right_outer_perp_x, 0, right_tc_mid_z - right_outer_perp_z)
      end

      # Create right outer web as a closed face (4 vertices)
      right_outer_web_vertices = [
        right_outer_bottom_plus,    # Bottom inner
        right_outer_top_plus,       # Top inner
        right_outer_top_minus,      # Top outer
        right_outer_bottom_minus    # Bottom outer
      ]
      right_outer_web_face = ents.add_face(right_outer_web_vertices)

      # ===== EXTRUDE WEB MEMBERS =====
      # Extrude all web faces to create 3D solids
      # Do EXACTLY what chords do: no reversal, just negative pushpull
      left_web_face.pushpull(-lumber_width) if left_web_face
      right_web_face.pushpull(-lumber_width) if right_web_face
      left_outer_web_face.pushpull(-lumber_width) if left_outer_web_face
      right_outer_web_face.pushpull(-lumber_width) if right_outer_web_face

      # Overlaps remain - solid tools approach didn't work with separate groups

      group.name = "Fink_Truss_#{span.to_i}ft_#{rise.to_i}-#{run.to_i}"
      group
    end

    # Queen post truss: two vertical posts
    def self.create_queen_post_truss(span, rise, run, origin = SU_MCP::ORIGIN, lumber_width = 1.5, lumber_depth = 3.5)
      half_span = span / 2.0
      peak_height = (half_span / run) * rise

      # Post positions (at 1/3 and 2/3 of span)
      left_post_x = span / 3.0
      right_post_x = span * 2.0 / 3.0
      post_height = peak_height * 0.7  # Posts are about 70% of peak height

      left_bottom = origin
      right_bottom = origin.offset(SU_MCP::X_AXIS, span)
      peak = origin.offset(SU_MCP::X_AXIS, half_span).offset(SU_MCP::Z_AXIS, peak_height)

      group = SU_MCP.entities.add_group
      truss_ents = group.entities

      # Bottom chord
      bottom_pts = [
        left_bottom,
        left_bottom.offset(SU_MCP::Z_AXIS, lumber_depth),
        right_bottom.offset(SU_MCP::Z_AXIS, lumber_depth),
        right_bottom
      ]
      truss_ents.add_face(bottom_pts).pushpull(-lumber_width)

      # Top chords
      # Left top chord
      left_top_pts = [
        left_bottom.offset(SU_MCP::Z_AXIS, lumber_depth),
        left_bottom.offset(SU_MCP::Z_AXIS, lumber_depth).offset(SU_MCP::X_AXIS, lumber_width),
        peak.offset(SU_MCP::X_AXIS, -lumber_width/2),
        peak.offset(SU_MCP::X_AXIS, -lumber_width/2).offset(SU_MCP::Z_AXIS, -lumber_depth)
      ]
      truss_ents.add_face(left_top_pts).pushpull(-lumber_width)

      # Right top chord
      right_top_pts = [
        peak.offset(SU_MCP::X_AXIS, lumber_width/2).offset(SU_MCP::Z_AXIS, -lumber_depth),
        peak.offset(SU_MCP::X_AXIS, lumber_width/2),
        right_bottom.offset(SU_MCP::Z_AXIS, lumber_depth).offset(SU_MCP::X_AXIS, -lumber_width),
        right_bottom.offset(SU_MCP::Z_AXIS, lumber_depth)
      ]
      truss_ents.add_face(right_top_pts).pushpull(-lumber_width)

      # Left queen post
      left_post_pts = [
        origin.offset(SU_MCP::X_AXIS, left_post_x - lumber_width/2).offset(SU_MCP::Z_AXIS, lumber_depth),
        origin.offset(SU_MCP::X_AXIS, left_post_x + lumber_width/2).offset(SU_MCP::Z_AXIS, lumber_depth),
        origin.offset(SU_MCP::X_AXIS, left_post_x + lumber_width/2).offset(SU_MCP::Z_AXIS, post_height),
        origin.offset(SU_MCP::X_AXIS, left_post_x - lumber_width/2).offset(SU_MCP::Z_AXIS, post_height)
      ]
      truss_ents.add_face(left_post_pts).pushpull(-lumber_width)

      # Right queen post
      right_post_pts = [
        origin.offset(SU_MCP::X_AXIS, right_post_x - lumber_width/2).offset(SU_MCP::Z_AXIS, lumber_depth),
        origin.offset(SU_MCP::X_AXIS, right_post_x + lumber_width/2).offset(SU_MCP::Z_AXIS, lumber_depth),
        origin.offset(SU_MCP::X_AXIS, right_post_x + lumber_width/2).offset(SU_MCP::Z_AXIS, post_height),
        origin.offset(SU_MCP::X_AXIS, right_post_x - lumber_width/2).offset(SU_MCP::Z_AXIS, post_height)
      ]
      truss_ents.add_face(right_post_pts).pushpull(-lumber_width)

      group.name = "Queen_Post_Truss_#{span.to_i}in"
      group
    end
  end
end
