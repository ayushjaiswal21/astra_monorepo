import json
import time
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from .models import Course, UserProgress, Lesson, QuizQuestion

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['course_id']
        self.room_group_name = f'chat_{self.room_name}'
        self.user = self.scope['user']

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        message_type = text_data_json.get('type', 'chat_message')

        if message_type == 'chat_message':
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': self.user.username,
                    'user_id': self.user.id,
                    'timestamp': int(time.time())
                }
            )
        elif message_type == 'progress_update':
            # Handle progress updates
            lesson_id = text_data_json.get('lesson_id')
            completed = text_data_json.get('completed', False)
            
            if lesson_id:
                success = await self.update_lesson_progress(lesson_id, completed)
                await self.send(text_data=json.dumps({
                    'type': 'progress_update',
                    'success': success,
                    'lesson_id': lesson_id,
                    'completed': completed,
                    'timestamp': int(time.time())
                }))

    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'username': event['username'],
            'user_id': event['user_id'],
            'type': 'chat_message',
            'timestamp': event.get('timestamp', int(time.time()))
        }))

    @database_sync_to_async
    def update_lesson_progress(self, lesson_id, completed):
        try:
            lesson = Lesson.objects.get(id=lesson_id)
            progress, created = UserProgress.objects.get_or_create(
                user=self.user,
                lesson=lesson,
                defaults={'completed': completed}
            )
            
            if not created:
                progress.completed = completed
                progress.save()
                
            return True
        except Lesson.DoesNotExist:
            return False


class LessonConsumer(WebsocketConsumer):
    def connect(self):
        self.lesson_id = self.scope['url_route']['kwargs']['lesson_id']
        self.room_group_name = f'lesson_{self.lesson_id}'
        self.user = self.scope['user']

        # Join lesson group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        # Leave lesson group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'quiz_submission':
            self.handle_quiz_submission(text_data_json)
        elif message_type == 'code_execution':
            self.handle_code_execution(text_data_json)
        elif message_type == 'user_activity':
            self.handle_user_activity(text_data_json)

    def handle_quiz_submission(self, data):
        question_id = data.get('question_id')
        selected_option = data.get('selected_option')
        
        try:
            question = QuizQuestion.objects.get(id=question_id)
            is_correct = selected_option == question.correct_answer
            
            # Update user progress
            progress, _ = UserProgress.objects.get_or_create(
                user=self.user,
                lesson=question.lesson
            )
            
            # Send response back to user
            self.send(text_data=json.dumps({
                'type': 'quiz_result',
                'is_correct': is_correct,
                'correct_answer': question.correct_answer,
                'explanation': f"The correct answer is {question.correct_answer}. {getattr(question, f'option_{question.correct_answer.lower()}')}"
            }))
            
            # Broadcast to all users in the lesson (for teacher view)
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'quiz_result_broadcast',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'question_id': question_id,
                    'is_correct': is_correct,
                    'timestamp': int(time.time())
                }
            )
            
        except QuizQuestion.DoesNotExist:
            self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Question not found'
            }))

    def handle_code_execution(self, data):
        code = data.get('code', '')
        # In a real implementation, you would execute the code in a sandbox
        # For now, we'll just echo it back
        self.send(text_data=json.dumps({
            'type': 'code_output',
            'output': f"Executed code: {code}",
            'timestamp': int(time.time())
        }))

    def handle_user_activity(self, data):
        # Broadcast user activity to all connected clients
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'user_activity_broadcast',
                'user_id': self.user.id,
                'username': self.user.username,
                'activity': data.get('activity', ''),
                'timestamp': int(time.time())
            }
        )

    def quiz_result_broadcast(self, event):
        # Send quiz results to all connected clients
        self.send(text_data=json.dumps({
            'type': 'quiz_result_broadcast',
            'user_id': event['user_id'],
            'username': event['username'],
            'question_id': event['question_id'],
            'is_correct': event['is_correct'],
            'timestamp': event['timestamp']
        }))

    def user_activity_broadcast(self, event):
        # Send user activity to all connected clients
        self.send(text_data=json.dumps({
            'type': 'user_activity',
            'user_id': event['user_id'],
            'username': event['username'],
            'activity': event['activity'],
            'timestamp': event['timestamp']
        }))


class TutorChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'tutor_chat'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        context = text_data_json.get('context', '')
        
        # Generate AI response
        ai_response = await self.generate_ai_response(message, context)
        
        # Send message back to WebSocket
        await self.send(text_data=json.dumps({
            'message': ai_response,
            'sender': 'ai',
            'timestamp': int(time.time())
        }))
    
    async def generate_ai_response(self, message, context):
        '''Generate a simulated AI response based on the message and context.'''
        # In a real implementation, this would call the Gemini API
        ai_responses = [
            f"That's an interesting question about '{message[:20]}...'. Let me explain it in a different way.",
            f"I understand you're asking about '{message[:20]}...'. Here's a helpful explanation:",
            f"Great question! Regarding '{message[:20]}...', here's what you should know:",
            f"Let me help clarify '{message[:20]}...' with this explanation:",
            f"I can see you're curious about '{message[:20]}...'. Let me break it down for you:"
        ]
        
        # Add context-aware response if context is provided
        if context:
            ai_responses.extend([
                f"Based on the lesson about {context[:30]}..., here's how I'd explain it:",
                f"In the context of {context[:30]}..., here's what I understand:",
                f"This relates to what we were learning about {context[:30]}... Let me explain:"
            ])
        
        # Add some educational content
        educational_phrases = [
            "A good way to think about this is like a real-world example.",
            "This concept is important because it helps us understand more complex topics later.",
            "Many beginners find this concept challenging at first, but with practice it becomes clearer.",
            "Let me give you an example to illustrate this point.",
            "This is a fundamental concept that will be useful in many different scenarios."
        ]
        
        # Combine the response parts
        response = ai_responses[0]
        
        return response
