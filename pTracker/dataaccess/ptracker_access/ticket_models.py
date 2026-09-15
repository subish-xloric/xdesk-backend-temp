from django.db import models
from django.contrib.auth.models import User
from django.conf import Settings, settings


# class Ticket(models.Model):
#     PRIORITY_CHOICES = [
#         ('Low', 'Low'),
#         ('Medium', 'Medium'),
#         ('High', 'High'),
#     ]

#     STATUS_CHOICES = [
#         ('Open', 'Open'),
#         ('In Progress', 'In Progress'),
#         ('To Test', 'To Test'),
#         ('Resolved', 'Resolved'),
#         ('Closed', 'Closed'),
#     ]

#     TICKET_TYPE_CHOICES = [
#         ('Feature', 'Feature'),
#         ('Enhancement', 'Enhancement'),
#         ('Bug', 'Bug'),
#         ('Task', 'Task'),
#     ]

#     ticket_id = models.AutoField(primary_key=True)
#     title = models.CharField(max_length=255)
#     description = models.TextField()
#     priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES)
#     ticket_type = models.CharField(max_length=20, choices=TICKET_TYPE_CHOICES)
#     project = models.ForeignKey(Project, on_delete=models.CASCADE)
#     created_by = models.ForeignKey(User, on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.title

# class Comment(models.Model):
#     comment_id = models.AutoField(primary_key=True)
#     ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     content = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)

# class Attachment(models.Model):
#     attachment_id = models.AutoField(primary_key=True)
#     ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
#     filename = models.CharField(max_length=255)
#     file_url = models.CharField(max_length=255)

# class TicketAssignment(models.Model):
#     assignment_id = models.AutoField(primary_key=True)
#     ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
#     assigned_to = models.ForeignKey(User, on_delete=models.CASCADE)
#     assigned_at = models.DateTimeField(auto_now_add=True)

# class TicketStatus(models.Model):
#     status_id = models.AutoField(primary_key=True)
#     ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
#     status = models.CharField(max_length=20, choices=Ticket.STATUS_CHOICES)
#     changed_at = models.DateTimeField(auto_now_add=True)

# class TicketPriority(models.Model):
#     priority_id = models.AutoField(primary_key=True)
#     ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
#     priority = models.CharField(max_length=10, choices=Ticket.PRIORITY_CHOICES)
#     changed_at = models.DateTimeField(auto_now_add=True)



class TicketHeader(models.Model):

    PRIORITY_CHOICES = settings.TICKETS_PRIORITY_CHOICES
    STATUS_CHOICES = settings.TICKETS_STATUS_CHOICES
    TICKET_TYPE_CHOICES = settings.TICKETS_TYPE_CHOICES
    TICKET_CATEGORIES = settings.TICKET_CATEGORIES

    ticket_id = models.AutoField(primary_key=True)
    subject = models.CharField(max_length=255)
    assigned_to = models.IntegerField(null=True, blank=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    ticket_type = models.CharField(max_length=20, choices=TICKET_TYPE_CHOICES)
    project_id = models.IntegerField(null=True, blank=True)
    tag_name = models.CharField(max_length=255)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    estimated_time = models.CharField(max_length=10)
    is_private = models.IntegerField(null=True, blank=True)
    milestone = models.CharField(max_length=255)
    parent_id = models.IntegerField(null=True, blank=True)
    category = models.CharField(null=True, blank=True, max_length=20, choices=TICKET_CATEGORIES)
    is_cicd_enabled = models.IntegerField(default=0)
    is_cicd_merged = models.IntegerField(default=0)
    repo_id = models.IntegerField()
    repo_uri = models.CharField(max_length=255, null=True, blank=True)
    module_id = models.IntegerField(default=0)

    def __str__(self):
        return self.subject

    class Meta:
        managed = False
        db_table = 'ticket_header'


class TicketDetails(models.Model):

    PRIORITY_CHOICES = settings.TICKETS_PRIORITY_CHOICES
    STATUS_CHOICES = settings.TICKETS_STATUS_CHOICES
    TICKET_TYPE_CHOICES = settings.TICKETS_TYPE_CHOICES
    TICKET_CATEGORIES = settings.TICKET_CATEGORIES

    ticket_details_id = models.AutoField(primary_key=True)
    ticket_id = models.IntegerField(null=True, blank=True)
    message = models.TextField()
    action = models.CharField(max_length=255) #Created, #Updated
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    ticket_type = models.CharField(max_length=20, choices=TICKET_TYPE_CHOICES)
    assigned_to = models.IntegerField(null=True, blank=True)
    is_header = models.IntegerField(null=True, blank=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deadline = models.DateTimeField(null=True, blank=True)
    category = models.CharField(null=True, blank=True, max_length=20, choices=TICKET_CATEGORIES)
    estimated_time = models.CharField(max_length=10)
    subject = models.CharField(max_length=255)
    module_id = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = 'ticket_details'


class TicketAttachment(models.Model):

    attachment_id = models.AutoField(primary_key=True)
    ticket_id = models.IntegerField(null=True, blank=True)
    filename = models.CharField(max_length=255)
    file = models.CharField(max_length=255)
    ticket_details_id = models.IntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'ticket_attachment'


class TicketWatcher(models.Model):

    watcher_id = models.AutoField(primary_key=True)
    ticket_id = models.IntegerField(null=True, blank=True)
    watcher = models.IntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'ticket_watcher'


class TicketLogTime(models.Model):

    ticket_time_id = models.AutoField(primary_key=True)
    ticket_id = models.IntegerField()
    user_id = models.IntegerField()
    log_date = models.DateField()
    log_time = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'ticket_log_time'