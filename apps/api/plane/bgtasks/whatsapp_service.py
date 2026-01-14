import logging
import os
from typing import Optional, Dict, Any

import requests
from django.utils import timezone

from plane.db.models import WhatsAppNotificationLog, User
from plane.utils.exception_logger import log_exception

logger = logging.getLogger("plane.worker")


class WhatsAppService:
    """Service class for sending WhatsApp notifications"""
    
    def __init__(self):
        """Initialize WhatsApp service with configuration from environment variables"""
        self.whatsapp_url = os.environ.get("WHATSAPP_API_URL")
        self.whatsapp_token = os.environ.get("WHATSAPP_API_TOKEN")
        
        if not self.whatsapp_url or not self.whatsapp_token:
            raise ValueError("WHATSAPP_API_URL and WHATSAPP_API_TOKEN must be set")
    
    def _send_message(self, phone_number: str, payload: Dict[str, Any]) -> bool:
        """
        Send WhatsApp message using Facebook Graph API
        
        Args:
            phone_number: Recipient phone number (with country code, e.g., +255123456789)
            payload: WhatsApp API payload dictionary (should contain "to" field or it will be set from phone_number)
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            # Ensure payload has the "to" field set
            if "to" not in payload:
                payload["to"] = phone_number
            
            response = requests.post(
                self.whatsapp_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.whatsapp_token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            
            if response.status_code != 200:
                logger.error(
                    f"WhatsApp send failed - Status: {response.status_code}, "
                    f"Response: {response.text}, "
                    f"To: {payload['to']}"
                )
                return False
            
            logger.info(f"WhatsApp message sent successfully to {payload['to']}")
            return True
            
        except Exception as e:
            logger.error(f"WhatsApp send error - To: {phone_number}, Error: {str(e)}")
            log_exception(e)
            return False
    
    def send_item_assigned_notification(
        self,
        receiver_id: str,
        triggered_by_id: str,
        entity_identifier: str,
        entity_name: str,
        assignee_name: str,
        assignor_name: str,
        task_name: str,
        task_priority: str,
        task_deadline: str,
        issue_key: str,
    ) -> Optional[WhatsAppNotificationLog]:
        """
        Log WhatsApp notification when a task/item is assigned
        The actual sending will be handled by the background task
        
        Args:
            receiver_id: UUID of the user receiving the notification
            triggered_by_id: UUID of the user who triggered the notification
            entity_identifier: UUID of the entity (issue/task)
            entity_name: Name of the entity
            assignee_name: Name of the assignee
            assignor_name: Name of the assignor
            task_name: Name of the task
            task_priority: Priority of the task
            task_deadline: Deadline of the task
            issue_key: External issue key (e.g. SAS-155) used in WhatsApp URL button
            
        Returns:
            WhatsAppNotificationLog instance if created, None otherwise
        """
        try:
            receiver = User.objects.get(pk=receiver_id)
            
            # Check if receiver has mobile number
            if not receiver.mobile_number:
                logger.info(f"User {receiver_id} does not have mobile number, skipping notification")
                return None
            
            # Create WhatsApp template payload matching the marketing template structure
            # Template parameters are passed separately, template is defined in WhatsApp Business Manager
            # Phone number will be set by the background task when sending
            
            payload = {
                "messaging_product": "whatsapp",
                "type": "template",
                "template": {
                    "name": "plane_assign_task",  # Template name - configure in WhatsApp Business Manager
                    "language": {
                        "code": "en"
                    },
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": assignee_name},
                                {"type": "text", "text": assignor_name},
                                {"type": "text", "text": task_name},
                                {"type": "text", "text": task_priority},
                                {"type": "text", "text": task_deadline}
                            ]
                        },
                        {
                            "type": "button",
                            "sub_type": "url",
                            "index": "0",
                            "parameters": [
                                {
                                    "type": "text",
                                    "text": issue_key,
                                }
                            ],
                        }
                    ]
                }
            }
            
            # Create notification log (background task will send it)
            notification_log = WhatsAppNotificationLog.objects.create(
                receiver_id=receiver_id,
                triggered_by_id=triggered_by_id,
                entity_identifier=entity_identifier,
                entity_name=entity_name,
                entity="issue",
                data=payload,
            )
            
            logger.info(f"WhatsApp notification logged for user {receiver_id}, will be sent by background task")
            return notification_log
            
        except User.DoesNotExist:
            logger.error(f"User {receiver_id} not found")
            return None
        except Exception as e:
            log_exception(e)
            logger.error(f"Error logging WhatsApp notification: {str(e)}")
            return None
