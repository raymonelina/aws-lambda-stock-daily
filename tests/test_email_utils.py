import pytest
from unittest.mock import Mock, patch
from aws_lambda_alpaca_daily.email_utils import send_status_email


@pytest.fixture
def mock_ses_client():
    return Mock()


def test_send_status_email_eventbridge_trigger_success(mock_ses_client, caplog):
    """Test successful email sending for EventBridge trigger."""
    mock_ses_client.send_email.return_value = {'MessageId': 'test-message-id'}
    
    with patch('aws_lambda_alpaca_daily.email_utils.boto3.client', return_value=mock_ses_client):
        result = send_status_email(
            is_eventbridge_trigger=True,
            subject="Test Subject",
            body="Test Body"
        )
    
    mock_ses_client.send_email.assert_called_once_with(
        Source='zhurunzhang@gmail.com',
        Destination={'ToAddresses': ['zhurunzhang@gmail.com']},
        Message={
            'Subject': {'Data': 'Test Subject'},
            'Body': {'Text': {'Data': 'Test Body'}}
        }
    )
    assert result == {'MessageId': 'test-message-id'}
    assert "Email sent successfully: Test Subject" in caplog.text


def test_send_status_email_eventbridge_trigger_failure(mock_ses_client, caplog):
    """Test email sending failure for EventBridge trigger."""
    mock_ses_client.send_email.side_effect = Exception("SES Error")
    
    with patch('aws_lambda_alpaca_daily.email_utils.boto3.client', return_value=mock_ses_client):
        result = send_status_email(
            is_eventbridge_trigger=True,
            subject="Test Subject",
            body="Test Body"
        )
    
    assert result is None
    assert "Failed to send email: SES Error" in caplog.text


def test_send_status_email_manual_trigger(caplog):
    """Test simulated email for manual trigger."""
    send_status_email(
        is_eventbridge_trigger=False,
        subject="Test Subject",
        body="Test Body"
    )
    
    assert "[SIMULATED EMAIL] Subject: Test Subject" in caplog.text
    assert "[SIMULATED EMAIL] Body: Test Body" in caplog.text


def test_send_status_email_custom_parameters(mock_ses_client):
    """Test email sending with custom parameters."""
    mock_ses_client.send_email.return_value = {'MessageId': 'test-message-id'}
    
    with patch('aws_lambda_alpaca_daily.email_utils.boto3.client', return_value=mock_ses_client):
        send_status_email(
            is_eventbridge_trigger=True,
            subject="Custom Subject",
            body="Custom Body",
            source_email="custom@example.com",
            destination_email="dest@example.com",
            region="us-east-1"
        )
    
    mock_ses_client.send_email.assert_called_once_with(
        Source='custom@example.com',
        Destination={'ToAddresses': ['dest@example.com']},
        Message={
            'Subject': {'Data': 'Custom Subject'},
            'Body': {'Text': {'Data': 'Custom Body'}}
        }
    )