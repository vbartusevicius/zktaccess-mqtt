import pytest
import json
import logging
from unittest.mock import patch, MagicMock, call

from mqtt.publisher import MQTTPublisher
from scheduler.jobs import JobScheduler
from core.models import DeviceDefinition

from tests.mocks.zk_access import MockZKAccess, MockZKSDKError

logging.basicConfig(level=logging.DEBUG)

class TestZKAccessToMQTT:   
    @pytest.fixture
    def mock_zk_access(self):
        connstr = "protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=test"
        mock_zk = MockZKAccess(connstr=connstr, device_model=MagicMock())
        mock_zk.parameters.serial_number = "TEST123456"
        return mock_zk
    
    @pytest.fixture
    def setup_test_environment(self, mock_zk_access):
        mqtt_client = MagicMock()
        publisher = MQTTPublisher(mqtt_client, mock_zk_access.parameters.serial_number)
        job_scheduler = JobScheduler(publisher)
        
        return (job_scheduler, publisher, mqtt_client, mock_zk_access)
    
    @patch('zkt.handler.ZKAccess')
    @patch('mqtt.handler.publish_message')
    def test_door_open_event_to_mqtt(self, mock_publish, mock_zk_class, setup_test_environment, mock_zk_access):
        job_scheduler, _, _, _ = setup_test_environment
        
        mock_zk_class.return_value = mock_zk_access
        door_open_event = mock_zk_access.generate_fake_event(
            event_code=0,  # Door open event
            door_number=1,
            card_id="12345"
        )
        
        mock_zk_access.add_events_to_queue([door_open_event])
        
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
    
    @patch('zkt.handler.ZKAccess')
    @patch('mqtt.handler.publish_message')
    def test_aux_input_event_to_mqtt(self, mock_publish, mock_zk_class, setup_test_environment, mock_zk_access):
        job_scheduler, _, _, _ = setup_test_environment
        
        mock_zk_class.return_value = mock_zk_access
        
        aux_input_event = mock_zk_access.generate_fake_event(
            event_code=221,  # Aux input connected
            door_number=2,   # Aux input 2
            card_id=None
        )
        
        mock_zk_access.add_events_to_queue([aux_input_event])
        
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
    
    @patch('zkt.handler.ZKAccess')
    @patch('mqtt.handler.publish_message')
    def test_multiple_sequential_events(self, mock_publish, mock_zk_class, setup_test_environment, mock_zk_access):
        job_scheduler, _, _, _ = setup_test_environment
        
        mock_zk_class.return_value = mock_zk_access
        
        events = [
            # Door 1 opening with card scan
            mock_zk_access.generate_fake_event(event_code=0, door_number=1, card_id="12345"),
            # Door 1 closing
            mock_zk_access.generate_fake_event(event_code=201, door_number=1, card_id=None),
            # Door 2 opening with card scan
            mock_zk_access.generate_fake_event(event_code=0, door_number=2, card_id="54321")
        ]
        
        mock_zk_access.add_events_to_queue(events)
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
    def test_state_initialization(self, mock_publish, mock_get_device_def, setup_test_environment, mock_zk_access):
        job_scheduler, _, _, _ = setup_test_environment
        model_name = mock_zk_access.device_model.__name__ if hasattr(mock_zk_access.device_model, '__name__') else 'Unknown'
        serial_number = mock_zk_access.parameters.serial_number
        
        device_def = DeviceDefinition(
            parameters=mock_zk_access.parameters,
            doors=mock_zk_access.doors,
            readers=mock_zk_access.readers,
            relays=mock_zk_access.relays,
            aux_inputs=mock_zk_access.aux_inputs
        )
        
        mock_get_device_def.return_value = device_def
        
        job_scheduler.initialize_states(device_def)
        
        # Verify the total number of messages
        expected_entity_count = (
            len(mock_zk_access.doors) +      # Door states
            len(mock_zk_access.readers) +    # Reader states
            len(mock_zk_access.relays) +     # Relay states
            len(mock_zk_access.aux_inputs)   # Aux input states
        )
        
        assert mock_publish.call_count >= expected_entity_count, \
            f"Expected at least {expected_entity_count} MQTT messages, got {mock_publish.call_count}"
        
        # Verify door states are published to the correct topics with appropriate payloads
        for door in mock_zk_access.doors:
            door_topic = f"zkt_eco/{model_name}/{serial_number}/door_{door.number}/state"
            door_calls = [call for call in mock_publish.call_args_list if call[0][1] == door_topic]
            assert door_calls, f"No state message published for door {door.number}"
            assert door_calls[0][0][2] in ["ON", "OFF"], f"Invalid door state payload: {door_calls[0][0][2]}"
        
        # Verify reader states
        for reader in mock_zk_access.readers:
            reader_topic = f"zkt_eco/{model_name}/{serial_number}/reader_{reader.number}_card/state"
            reader_calls = [call for call in mock_publish.call_args_list if reader_topic in call[0][1]]
            assert reader_calls, f"No state message published for reader {reader.number}"
        
        # Verify relay states
        for relay in mock_zk_access.relays:
            # StateManager formats relay IDs using both group name and number
            relay_topic = f"zkt_eco/{model_name}/{serial_number}/relay_{relay.group.name}_{relay.number}/state"
            relay_calls = [call for call in mock_publish.call_args_list if relay_topic in call[0][1]]
            assert relay_calls, f"No state message published for relay {relay.group.name}_{relay.number}"
            assert relay_calls[0][0][2] in ["ON", "OFF"], f"Invalid relay state payload: {relay_calls[0][0][2]}"
        
        # Verify aux input states
        for aux in mock_zk_access.aux_inputs:
            aux_topic = f"zkt_eco/{model_name}/{serial_number}/aux_input_{aux.number}/state"
            aux_calls = [call for call in mock_publish.call_args_list if aux_topic in call[0][1]]
            assert aux_calls, f"No state message published for aux input {aux.number}"
            assert aux_calls[0][0][2] in ["ON", "OFF"], f"Invalid aux input state payload: {aux_calls[0][0][2]}"
            
    @patch('zkt.handler.ZKAccess')
    @patch('mqtt.handler.publish_message')
    def test_error_handling(self, mock_publish, mock_zk_class, setup_test_environment):
        job_scheduler, _, _, mock_zk_access = setup_test_environment
        
        mock_zk_class.side_effect = MockZKSDKError("Connection failed", 5)
        job_scheduler.polling_job()
        
        assert mock_publish.call_count == 0, "Expected no MQTT messages during error condition"
        job_scheduler.polling_job()
        
        assert mock_publish.call_count == 0, "Expected no MQTT messages during error condition"
        
        mock_zk_class.side_effect = None
        mock_zk_class.return_value = mock_zk_access
        
        door_event = mock_zk_access.generate_fake_event(
            event_code=0, door_number=1, card_id="12345"
        )
        mock_zk_access.add_events_to_queue([door_event])
        
        with patch('zkt.handler.poll_zkteco_changes', return_value=[door_event]):
            job_scheduler.polling_job()
            assert mock_publish.call_count > 0, "Expected MQTT messages after recovery"
