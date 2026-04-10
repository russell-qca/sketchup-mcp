# frozen_string_literal: true

module Construction
  # MedeekFoundationReader - Read attributes from existing Medeek Foundation assemblies
  class MedeekFoundationReader
    # Check if Medeek Foundation Plugin is installed
    def self.available?
      begin
        defined?(Medeek_Engineering_Inc_Extensions::MedeekFoundationPlugin::Sog::MedeekMethods)
      rescue
        false
      end
    end

    # Read all attributes from a foundation assembly
    def self.read_all_attributes(params = {})
      unless available?
        raise "Medeek Foundation Plugin not installed. Please install from SketchUp Extension Warehouse."
      end

      group_name = params['group_name']

      begin
        # Get Medeek Foundation API
        medeek = Medeek_Engineering_Inc_Extensions::MedeekFoundationPlugin::Sog::MedeekMethods

        # Get the foundation group
        foundation_group = find_foundation_group(group_name)

        unless foundation_group
          return {
            status: 'error',
            message: 'No foundation assembly found. Please select a foundation or provide a group name.'
          }
        end

        # Read all attributes
        attributes = medeek.sog_read_attributes(foundation_group)

        if attributes
          {
            status: 'success',
            group_name: foundation_group.name,
            attributes: attributes,
            message: "Read #{attributes.keys.length} attributes from foundation assembly"
          }
        else
          {
            status: 'error',
            message: 'Failed to read attributes. The selected object may not be a valid Medeek Foundation assembly.'
          }
        end

      rescue => e
        {
          status: 'error',
          message: "Error reading foundation attributes: #{e.message}"
        }
      end
    end

    # Read a specific attribute from a foundation assembly
    def self.read_attribute(params = {})
      unless available?
        raise "Medeek Foundation Plugin not installed. Please install from SketchUp Extension Warehouse."
      end

      attribute_name = params['attribute_name']
      group_name = params['group_name']

      unless attribute_name
        return {
          status: 'error',
          message: 'Attribute name is required'
        }
      end

      begin
        # Get Medeek Foundation API
        medeek = Medeek_Engineering_Inc_Extensions::MedeekFoundationPlugin::Sog::MedeekMethods

        # Get the foundation group
        foundation_group = find_foundation_group(group_name)

        unless foundation_group
          return {
            status: 'error',
            message: 'No foundation assembly found. Please select a foundation or provide a group name.'
          }
        end

        # Read specific attribute
        value = medeek.sog_read_attribute(attribute_name, foundation_group)

        if value
          {
            status: 'success',
            group_name: foundation_group.name,
            attribute_name: attribute_name,
            value: value,
            message: "#{attribute_name} = #{value}"
          }
        else
          {
            status: 'error',
            message: "Attribute '#{attribute_name}' not found or could not be read"
          }
        end

      rescue => e
        {
          status: 'error',
          message: "Error reading foundation attribute: #{e.message}"
        }
      end
    end

    private

    # Find a foundation group by name or from selection
    def self.find_foundation_group(group_name)
      if group_name && !group_name.empty?
        # Search for group by name
        SU_MCP.model.entities.grep(Sketchup::Group).find { |g| g.name == group_name }
      else
        # Try to get from current selection
        SU_MCP.model.selection.grep(Sketchup::Group).first
      end
    end
  end
end
