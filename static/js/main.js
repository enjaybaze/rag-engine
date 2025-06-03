document.addEventListener('DOMContentLoaded', function () {
    const modelSelector = document.getElementById('model_type');
    const selfDeployedFields = document.getElementById('self_deployed_fields');
    const projectIdField = document.getElementById('project_id_field');
    const locationField = document.getElementById('location_field');
    const endpointIdField = document.getElementById('endpoint_id_field');

    function toggleSelfDeployedFields() {
        if (modelSelector.value === 'self-deployed') {
            selfDeployedFields.style.display = 'block';
            projectIdField.querySelector('input').required = true;
            locationField.querySelector('input').required = true;
            endpointIdField.querySelector('input').required = true;
        } else {
            selfDeployedFields.style.display = 'none';
            projectIdField.querySelector('input').required = false;
            locationField.querySelector('input').required = false;
            endpointIdField.querySelector('input').required = false;
        }
    }

    // Initial check
    if (modelSelector) {
        toggleSelfDeployedFields();
        modelSelector.addEventListener('change', toggleSelfDeployedFields);
    }
});
