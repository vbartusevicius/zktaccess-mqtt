import os
import pytest
import tempfile
from unittest.mock import patch
from core.state_manager import StateManager
from core.models import DeviceDefinition


class TestStateManager:
    @pytest.fixture
    def temp_state_file(self):
        fd, path = tempfile.mkstemp()
        yield path
        os.close(fd)
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def sample_device_definition(self):
        return DeviceDefinition(
            parameters={"serial_number": "1234567890"},
            doors=[{"number": 1}],
            aux_inputs=[{"number": 1}],
            relays=[{"number": 1}],
            readers=[{"number": 1}]
        )

    def test_save_and_load_state(self, temp_state_file):
        state_manager = StateManager(temp_state_file)

        state_manager.update_state("door_1", "ON")
        state_manager.update_state("aux_input_1", "OFF")
        state_manager.update_state("reader_1_card", '{"card_id": "12345"}')

        new_state_manager = StateManager(temp_state_file)

        assert new_state_manager.get_state("door_1") == "ON"
        assert new_state_manager.get_state("aux_input_1") == "OFF"
        assert new_state_manager.get_state("reader_1_card") == '{"card_id": "12345"}'

    def test_initialize_from_device_with_persisted_state(self, temp_state_file, sample_device_definition):
        state_manager = StateManager(temp_state_file)
        state_manager.update_state("door_1", "ON")
        state_manager.update_state("aux_input_1", "OFF")
        state_manager.update_state("relay_lock_1", "ON")
        state_manager.update_state("reader_1_card", '{"card_id": "12345"}')

        new_state_manager = StateManager(temp_state_file)
        
        states = new_state_manager.initialize_from_device(sample_device_definition)

        door_state = next((s for s in states if s.entity_id == "door_1"), None)
        assert door_state is not None
        assert door_state.state == "ON"

        aux_state = next((s for s in states if s.entity_id == "aux_input_1"), None)
        assert aux_state is not None
        assert aux_state.state == "OFF"

        relay_state = next((s for s in states if s.entity_id == "relay_lock_1"), None)
        assert relay_state is not None
        assert relay_state.state == "ON"

        reader_state = next((s for s in states if s.entity_id == "reader_1_card"), None)
        assert reader_state is not None
        assert reader_state.state == '{"card_id": "12345"}'

    def test_initialize_from_device_with_no_persisted_state(self, temp_state_file, sample_device_definition):
        state_manager = StateManager(temp_state_file)
        
        states = state_manager.initialize_from_device(sample_device_definition)

        door_state = next((s for s in states if s.entity_id == "door_1"), None)
        assert door_state is not None
        assert door_state.state == "OFF"

        aux_state = next((s for s in states if s.entity_id == "aux_input_1"), None)
        assert aux_state is not None
        assert aux_state.state == "OFF"

        relay_state = next((s for s in states if s.entity_id == "relay_lock_1"), None)
        assert relay_state is not None
        assert relay_state.state == "OFF"

        reader_state = next((s for s in states if s.entity_id == "reader_1_card"), None)
        assert reader_state is not None
        assert reader_state.state == '{ "card_id": "0" }'

    def test_load_state_file_not_exists(self):
        non_existent_path = "/path/to/nonexistent/file.json"
        state_manager = StateManager(non_existent_path)
        
        assert state_manager.get_states() == {}

    def test_load_state_with_invalid_json(self, temp_state_file):
        with open(temp_state_file, 'w') as f:
            f.write('{"entity_states": {"invalid_json')
        
        state_manager = StateManager(temp_state_file)
        
        assert state_manager.get_states() == {}

    def test_save_state_file_permission_error(self):
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            state_manager = StateManager("/fake/path")
            state_manager.update_state("test", "value")
            assert state_manager.get_state("test") == "value"
