# frozen_string_literal: true

# Construction module - Contains all construction-related functionality
# for creating structural elements in SketchUp
module Construction
end

# Load all construction submodules
require_relative 'construction/roof_truss'
require_relative 'construction/wall'
require_relative 'construction/medeek_truss'
require_relative 'construction/medeek_foundation'
require_relative 'construction/medeek_foundation_reader'
