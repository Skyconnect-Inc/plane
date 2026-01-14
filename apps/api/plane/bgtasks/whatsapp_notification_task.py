import logging

# Third party imports
from celery import shared_task

# Django imports
from django.utils import timezone

# Module imports
from plane.db.models import WhatsAppNotificationLog, User
from plane.settings.redis import redis_instance
from plane.utils.exception_logger import log_exception
from plane.bgtasks.whatsapp_service import WhatsAppService

logger = logging.getLogger("plane.worker")


# acquire and delete redis lock
def acquire_lock(lock_id, expire_time=300):
    redis_client = redis_instance()
    """Attempt to acquire a lock with a specified expiration time."""
    return redis_client.set(lock_id, "true", nx=True, ex=expire_time)


def release_lock(lock_id):
    """Release a lock."""
    redis_client = redis_instance()
    redis_client.delete(lock_id)


@shared_task
def stack_whatsapp_notification():
    """Process all pending WhatsApp notifications"""
    # get all WhatsApp notifications
    whatsapp_notifications = WhatsAppNotificationLog.objects.filter(
        processed_at__isnull=True
    ).order_by("receiver").values()

    # Convert to unique receivers list
    receivers = list(set([str(notification.get("receiver_id")) for notification in whatsapp_notifications]))
    processed_notifications = []
    
    # Loop through all the receivers to create the WhatsApp messages
    for receiver_id in receivers:
        # Notification triggered for the receiver
        receiver_notifications = [
            notification for notification in whatsapp_notifications 
            if str(notification.get("receiver_id")) == receiver_id
        ]
        
        whatsapp_notification_ids = []
        for receiver_notification in receiver_notifications:
            # append processed notifications
            processed_notifications.append(receiver_notification.get("id"))
            whatsapp_notification_ids.append(receiver_notification.get("id"))
            
            # Send WhatsApp notification
            send_whatsapp_notification.delay(
                receiver_id=receiver_id,
                notification_id=receiver_notification.get("id"),
                whatsapp_notification_ids=whatsapp_notification_ids,
            )

    # Update the WhatsApp notification log
    if processed_notifications:
        WhatsAppNotificationLog.objects.filter(pk__in=processed_notifications).update(
            processed_at=timezone.now()
        )
        logger.info(f"Processing {len(processed_notifications)} WhatsApp notifications")


@shared_task
def send_whatsapp_notification(receiver_id, notification_id, whatsapp_notification_ids):
    """Send a single WhatsApp notification"""
    lock_id = f"send_whatsapp_notif_{receiver_id}_{notification_id}"
    
    try:
        if acquire_lock(lock_id=lock_id):
            receiver = User.objects.get(pk=receiver_id)
            notification = WhatsAppNotificationLog.objects.get(pk=notification_id)
            
            # Check if receiver has mobile number
            if not receiver.mobile_number:
                logger.warning(f"Skipping WhatsApp notification - User {receiver_id} has no mobile number")
                release_lock(lock_id=lock_id)
                return
            
            # Get payload from notification data (already has all dynamic data filled in by service)
            payload = notification.data
            if not payload:
                logger.error(f"Skipping WhatsApp notification {notification_id} - No payload data")
                release_lock(lock_id=lock_id)
                return
            
            # Add phone number to payload (service doesn't include it, background task adds it)
            payload["to"] = receiver.mobile_number
            
            # Initialize WhatsApp service and send message
            whatsapp_service = WhatsAppService()
            success = whatsapp_service._send_message(
                phone_number=receiver.mobile_number,
                payload=payload,
            )
            
            if success:
                # Update the logs
                WhatsAppNotificationLog.objects.filter(
                    pk__in=whatsapp_notification_ids
                ).update(sent_at=timezone.now())
            
            # release the lock
            release_lock(lock_id=lock_id)
            return
        else:
            logger.info(f"Duplicate WhatsApp notification {notification_id}, skipping")
            return
    except User.DoesNotExist:
        logger.error(f"User {receiver_id} not found for notification {notification_id}")
        release_lock(lock_id=lock_id)
        return
    except WhatsAppNotificationLog.DoesNotExist:
        logger.error(f"WhatsApp notification {notification_id} not found")
        release_lock(lock_id=lock_id)
        return
    except Exception as e:
        logger.error(f"WhatsApp notification error - Notification: {notification_id}, Error: {str(e)}")
        log_exception(e)
        release_lock(lock_id=lock_id)
        return
