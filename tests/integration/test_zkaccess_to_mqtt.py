import pytest
import json
import logging
from unittest.mock import patch, MagicMock

from mqtt.publisher import MQTTPublisher
from scheduler.jobs import JobScheduler
from core.models import DeviceDefinition
from c3.consts import EventType as C3EventType, VerificationMode
from core.state_manager import StateManager
import settings

from tests.mocks.c3 import MockC3

logging.basicConfig(level=logging.DEBUG)

class TestZKAccessToMQTT:   
    @pytest.fixture
    def mock_c3(self):
        mock_c3 = MockC3(ip="192.168.1.201", port=4370)
        return mock_c3
    
    @pytest.fixture
    def setup_test_environment(self, mock_c3):
        mqtt_client = MagicMock()
        publisher = MQTTPublisher(mqtt_client, mock_c3.serial_number)
        state_manager = StateManager(settings.STATE_FILE_PATH)
        job_scheduler = JobScheduler(publisher, state_manager)
        
        return (job_scheduler, publisher, mqtt_client, mock_c3)
    
    @patch('zkt.handler.C3')
    @patch('mqtt.handler.publish_message')
    def test_door_open_event_to_mqtt(self, mock_publish, mock_c3_class, setup_test_environment, mock_c3):
        job_scheduler, _, _, _ = setup_test_environment
        
        mock_c3_class.return_value = mock_c3
        door_open_event = mock_c3.generate_event(
            port_nr=1,
            card_no=12345,
            event_type=C3EventType.NORMAL_PUNCH_OPEN,
            verified=VerificationMode.CARD
        )
        
        mock_c3.add_events_to_queue([door_open_event])
        
        with patch('zkt.handler.poll_zkteco_changes', return_value=[door_open_event]):
            job_scheduler.polling_job()
            
            assert mock_publish.call_count > 0, "No MQTT messages were published"
            
            door_state_calls = [
                call_args for call_args in mock_publish.call_args_list 
                if "door_1/state" in call_args[0][1]
            ]
            assert door_state_calls, "No door state update was published"
            
            door_state_payload = door_state_calls[0][0][2]  # args[0][2] is the payload
            assert door_state_payload == "ON", f"Door state should be ON, got {door_state_payload}"
            
            reader_event_calls = [
                call_args for call_args in mock_publish.call_args_list 
                if "reader_1_scan" in call_args[0][1]
            ]
            assert reader_event_calls, "No reader event was published"
            
            if reader_event_calls:
                reader_payload = reader_event_calls[0][0][2]  # args[0][2] is the payload
                try:
                    payload_data = json.loads(reader_payload)
                    assert "card_id" in payload_data, "Card ID missing from reader event payload"
                    assert payload_data["card_id"] == "12345", f"Expected card ID 12345, got {payload_data['card_id']}"
                except json.JSONDecodeError:
                    pytest.fail(f"Failed to parse reader event payload: {reader_payload}")
            
            # Check reader scan state
            reader_scan_calls = [
                call_args for call_args in mock_publish.call_args_list 
                if "reader_1_scan/state" in call_args[0][1]
            ]
            assert reader_scan_calls, "No reader scan event was published"
            
            if reader_scan_calls:
                reader_scan_payload = reader_scan_calls[0][0][2]  # args[0][2] is the payload
                try:
                    scan_payload_data = json.loads(reader_scan_payload)
                    assert "card_id" in scan_payload_data, "Card ID missing from reader scan payload"
                    assert scan_payload_data["card_id"] == "12345", f"Expected card ID 12345, got {scan_payload_data['card_id']}"
                except json.JSONDecodeError:
                    pytest.fail(f"Failed to parse reader scan payload: {reader_scan_payload}")
            
            # Check reader card state
            reader_card_calls = [
                call_args for call_args in mock_publish.call_args_list 
                if "reader_1_card/state" in call_args[0][1]
            ]
            assert reader_card_calls, "No reader card state was published"
            
            reader_card_payload = reader_card_calls[0][0][2]  # args[0][2] is the payload
            try:
                card_payload_data = json.loads(reader_card_payload)
                assert "card_id" in card_payload_data, "Card ID missing from reader card payload"
                assert card_payload_data["card_id"] == "12345", f"Expected card ID 12345, got {card_payload_data['card_id']}"
                
                # Verify we have all the expected fields in the card payload
                expected_fields = ["event_type", "door_id", "reader_id", "timestamp", "zk_event_code", "zk_event_desc", "card_id"]
                for field in expected_fields:
                    assert field in card_payload_data, f"Expected field '{field}' missing from card payload"
            except json.JSONDecodeError:
                pytest.fail(f"Failed to parse reader card payload: {reader_card_payload}")
    
    @patch('zkt.handler.C3')
    @patch('mqtt.handler.publish_message')
    def test_aux_input_event_to_mqtt(self, mock_publish, mock_c3_class, setup_test_environment, mock_c3):
        job_scheduler, _, _, _ = setup_test_environment
        
        mock_c3_class.return_value = mock_c3
        
        aux_input_event = mock_c3.generate_event(
            port_nr=2,  # Aux input 2
            card_no=0,
            event_type=C3EventType.AUX_INPUT_SHORT,  # Aux input connected
            verified=VerificationMode.NONE
        )
        
        mock_c3.add_events_to_queue([aux_input_event])
        
        with patch('zkt.handler.poll_zkteco_changes', return_value=[aux_input_event]):
            job_scheduler.polling_job()
            
            assert mock_publish.call_count > 0, "No MQTT messages were published"
            
            aux_state_calls = [
                call_args for call_args in mock_publish.call_args_list 
                if "aux_input_2/state" in call_args[0][1]
            ]
            assert aux_state_calls, "No aux input state update was published"
            
            aux_state_payload = aux_state_calls[0][0][2]  # args[0][2] is the payload
            assert aux_state_payload == "ON", f"Aux input state should be ON, got {aux_state_payload}"
    
    @patch('zkt.handler.C3')
    @patch('mqtt.handler.publish_message')
    def test_multiple_sequential_events(self, mock_publish, mock_c3_class, setup_test_environment, mock_c3):
        job_scheduler, _, _, _ = setup_test_environment
        
        mock_c3_class.return_value = mock_c3
        
        events = [
            # Door 1 opening with card scan
            mock_c3.generate_event(port_nr=1, card_no=12345, event_type=C3EventType.NORMAL_PUNCH_OPEN),
            # Door 1 closing
            mock_c3.generate_event(port_nr=1, event_type=C3EventType.DOOR_CLOSED_CORRECT),
            # Door 2 opening with card scan
            mock_c3.generate_event(port_nr=2, card_no=54321, event_type=C3EventType.NORMAL_PUNCH_OPEN)
        ]
        
        mock_c3.add_events_to_queue(events)
        events_copy = events.copy()
        def poll_side_effect():
            if not events_copy:
                return []
            return [events_copy.pop(0)]
        
        with patch('zkt.handler.poll_zkteco_changes', side_effect=poll_side_effect):
            for _ in range(len(events)):
                mock_publish.reset_mock()
                job_scheduler.polling_job()
                
                assert mock_publish.call_count > 0, "No MQTT messages were published"
    
    @patch('zkt.handler.get_device_definition')
    @patch('mqtt.handler.publish_message')
    def test_state_initialization(self, mock_publish, mock_get_device_def, setup_test_environment, mock_c3):
        job_scheduler, _, _, _ = setup_test_environment
        model_name = settings.ZKT_DEVICE_MODEL
        serial_number = mock_c3.serial_number
        
        # Create mock device components for the device definition
        doors = [
            {'number': 1, 'name': 'Door 1'},
            {'number': 2, 'name': 'Door 2'}
        ]
        readers = [
            {'number': 1, 'name': 'Reader 1'},
            {'number': 2, 'name': 'Reader 2'}
        ]
        relays = [
            {'number': 1, 'name': 'Relay 1'},
            {'number': 2, 'name': 'Relay 2'}
        ]
        aux_inputs = [
            {'number': 1, 'name': 'AUX 1'},
            {'number': 2, 'name': 'AUX 2'}
        ]
        
        device_def = DeviceDefinition(
            parameters={'serial_number': serial_number, 'device_model': model_name},
            doors=doors,
            readers=readers,
            relays=relays,
            aux_inputs=aux_inputs
        )
        
        mock_get_device_def.return_value = device_def
        
        job_scheduler.initialize_states(device_def)
        
        # Verify the total number of messages
        expected_entity_count = (
            len(device_def.doors) +      # Door states
            len(device_def.readers) +    # Reader states
            len(device_def.relays) +     # Relay states
            len(device_def.aux_inputs)   # Aux input states
        )
        
        assert mock_publish.call_count >= expected_entity_count, \
            f"Expected at least {expected_entity_count} MQTT messages, got {mock_publish.call_count}"
        
        # Verify door states are published to the correct topics with appropriate payloads
        for door in device_def.doors:
            door_topic = f"zkt_eco/{model_name}/{serial_number}/door_{door['number']}/state"
            door_calls = [call for call in mock_publish.call_args_list if call[0][1] == door_topic]
            assert door_calls, f"No state message published for door {door['number']}"
            assert door_calls[0][0][2] in ["ON", "OFF"], f"Invalid door state payload: {door_calls[0][0][2]}"
        
        # Verify reader states
        for reader in device_def.readers:
            reader_topic = f"zkt_eco/{model_name}/{serial_number}/reader_{reader['number']}_card/state"
            reader_calls = [call for call in mock_publish.call_args_list if reader_topic in call[0][1]]
            assert reader_calls, f"No state message published for reader {reader['number']}"
        
        # Verify relay states
        for relay in device_def.relays:
            relay_topic = f"zkt_eco/{model_name}/{serial_number}/relay_lock_{relay['number']}/state"
            relay_calls = [call for call in mock_publish.call_args_list if relay_topic in call[0][1]]
            assert relay_calls, f"No state message published for relay lock_{relay['number']}"
            assert relay_calls[0][0][2] in ["ON", "OFF"], f"Invalid relay state payload: {relay_calls[0][0][2]}"
        
        # Verify aux input states
        for aux in device_def.aux_inputs:
            aux_topic = f"zkt_eco/{model_name}/{serial_number}/aux_input_{aux['number']}/state"
            aux_calls = [call for call in mock_publish.call_args_list if aux_topic in call[0][1]]
            assert aux_calls, f"No state message published for aux input {aux['number']}"
            assert aux_calls[0][0][2] in ["ON", "OFF"], f"Invalid aux input state payload: {aux_calls[0][0][2]}"
            
    @patch('zkt.handler.C3')
    @patch('mqtt.handler.publish_message')
    def test_error_handling(self, mock_publish, mock_c3_class, setup_test_environment, mock_c3):
        job_scheduler, _, _, _ = setup_test_environment
        
        # Simulate a connection error
        mock_c3_class.side_effect = Exception("Connection failed")
        job_scheduler.polling_job()
        
        assert mock_publish.call_count == 0, "Expected no MQTT messages during error condition"
        job_scheduler.polling_job()
        
        assert mock_publish.call_count == 0, "Expected no MQTT messages during error condition"
        
        mock_c3_class.side_effect = None
        mock_c3_class.return_value = mock_c3
        
        door_event = mock_c3.generate_event(
            port_nr=1,
            card_no=12345,
            event_type=C3EventType.NORMAL_PUNCH_OPEN,
            verified=VerificationMode.CARD
        )
        mock_c3.add_events_to_queue([door_event])
        
        with patch('zkt.handler.poll_zkteco_changes', return_value=[door_event]):
            job_scheduler.polling_job()
            assert mock_publish.call_count > 0, "Expected MQTT messages after recovery"
