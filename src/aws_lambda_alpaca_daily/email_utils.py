import boto3
import logging

logger = logging.getLogger(__name__)


def send_status_email(is_eventbridge_trigger, subject, body, source_email='zhurunzhang@gmail.com', destination_email='zhurunzhang@gmail.com', region='us-west-2'):
    """Sends status email if triggered by EventBridge, otherwise logs the message."""
    if is_eventbridge_trigger:
        try:
            ses = boto3.client('ses', region_name=region)
            response = ses.send_email(
                Source=source_email,
                Destination={'ToAddresses': [destination_email]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {'Text': {'Data': body}}
                }
            )
            logger.info(f"Email sent successfully: {subject}")
            return response
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    else:
        logger.info(f"[SIMULATED EMAIL] Subject: {subject}")
        logger.info(f"[SIMULATED EMAIL] Body: {body}")