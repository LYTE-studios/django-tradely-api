from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stripe_payment_intent_id = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.stripe_payment_intent_id} - {self.status}"


class Email(models.Model):
    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("pending", "Pending"),
    ]

    id = models.AutoField(primary_key=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    recipient_list = (
        models.TextField()
    )  # Consider changing to JSON field or ManyToManyField if needed
    created_at = models.DateTimeField(auto_now_add=True)
    sent_mail_status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="pending"
    )
    delivery_time = models.DateTimeField(null=True, blank=True)
    # When is_schedule = True, 0 is scheduled , 1 is canceled , 2 sent the message.

    def __str__(self):
        return self.subject
