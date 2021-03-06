from .models import Message
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.forms import ModelForm
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from Users.views import get_friends_matrix
from django.contrib.auth.models import User
from django.db.models import Q
from Constraint.models import Constraint
from Wallet.models import Wallet
from django.contrib import messages

class Message_Create(LoginRequiredMixin,CreateView):
    model = Message
    fields = ['message','receiver']
    template_name = 'Messages/create_message.html'
    context_object_name = 'messages'

    def form_valid(self,form):
        form.instance.sender = self.request.user
        constraint = Constraint.objects.get(owner = self.request.user)
        if constraint.user_type == 'commercial':
            return super().form_valid(form)
        else:
            data = get_friends_matrix(self.request.user)
            friend = form.instance.receiver
            if friend in data['friends']:
                return super().form_valid(form)
            else:
                return redirect('messages_view')


def message_view(request):
    if request.user.is_authenticated:
        constraints = Constraint.objects.filter(user_type='commercial')
        all_messages = []
        for constraint in constraints:
            messages = Message.objects.filter(sender=constraint.owner,receiver=request.user)
            if messages:
                all_messages.append(messages)
        print(all_messages)
        data = get_friends_matrix(request.user)
        friends_usernames = []
        for i in data['friends']:
            friends_usernames.append(i.username)
        return render(request, 'Messages/message_view.html',{"friends_usernames":friends_usernames,'ads':all_messages})
    messages.success(request, f'Login first')
    return redirect('login')


@login_required
def chat(request,username):
    if request.user.is_authenticated:
        friend = User.objects.get(username = username)
        data = get_friends_matrix(request.user)
        if friend in data['friends']:
            messages = Message.objects.filter(Q(sender=friend,receiver=request.user) | Q(sender=request.user,receiver=friend)).order_by('date_posted')
            return render(request,'Messages/chat.html',{'messages':messages})
        else:
            messages.success(request, f'You are not his/her friend')
            return redirect('messages_view')
    else:
        messages.success(request, f'Login first')
        return redirect('login')