from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status
from .serializers import SignupSerializer, ProfileSerializer, MessageSerializer
from .models import Profile, Message
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q


class SignupView(APIView):
    def post(self, request):
        print("Signup request data:", request.data)
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Signup successful"}, status=drf_status.HTTP_201_CREATED)
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = Profile.objects.get(user=request.user)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

    def patch(self, request):
        profile = Profile.objects.get(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)


class ProfileDetailView(APIView):
    def get(self, request, username):
        try:
            user = User.objects.get(username=username)
            profile = Profile.objects.get(user=user)
            serializer = ProfileSerializer(profile)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)
        except Profile.DoesNotExist:
            return Response({"detail": "Profile not found"}, status=404)


class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        other_user = User.objects.get(username=username)

        messages = Message.objects.filter(
            sender__in=[request.user, other_user],
            receiver__in=[request.user, other_user]
        ).order_by("timestamp")

        # Mark all messages from other_user as seen
        Message.objects.filter(
            sender=other_user,
            receiver=request.user,
            status="sent"  # only unread messages
        ).update(status="seen")

        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)


# Single chat history
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def messages_view(request, username):
    try:
        other_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"detail": "User not found"}, status=404)

    messages = Message.objects.filter(
        (Q(sender=request.user) & Q(receiver=other_user)) |
        (Q(sender=other_user) & Q(receiver=request.user))
    ).order_by("timestamp")

    messages_data = [
        {
            "id": m.id,
            "sender": m.sender.username,
            "receiver": m.receiver.username,
            "message": m.content,
            "timestamp": m.timestamp.isoformat(),
            "status": m.status
        }
        for m in messages
    ]

    # mark delivered messages as seen
    Message.objects.filter(sender=other_user, receiver=request.user, status="delivered").update(status="seen")

    return Response(messages_data)


class ChatListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        messages = Message.objects.filter(Q(sender=user) | Q(receiver=user))
        partner_ids = set()
        for m in messages:
            if m.sender_id != user.id:
                partner_ids.add(m.sender_id)
            if m.receiver_id != user.id:
                partner_ids.add(m.receiver_id)

        partners = User.objects.filter(id__in=partner_ids)
        chat_list = []

        for partner in partners:
            last_message = Message.objects.filter(
                (Q(sender=user) & Q(receiver=partner)) |
                (Q(sender=partner) & Q(receiver=user))
            ).order_by('-timestamp').first()

            unread = Message.objects.filter(
                sender=partner,
                receiver=user,
                status="delivered"  # delivered but not seen
            ).count()

            chat_list.append({
                "id": partner.id,
                "username": partner.username,
                "last_message": last_message.content if last_message else "",
                "last_message_timestamp": last_message.timestamp.isoformat() if last_message else None,
                "unread": unread,
            })

        chat_list.sort(key=lambda x: x["last_message_timestamp"] or "", reverse=True)
        return Response(chat_list)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_seen(request, message_id):
    try:
        message = Message.objects.get(id=message_id, receiver=request.user)
        message.status = "seen"
        message.save()
        return Response({"status": "seen"})
    except Message.DoesNotExist:
        return Response({"detail": "Not found"}, status=404)
