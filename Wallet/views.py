from django.shortcuts import render
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django import forms
from django.contrib.auth.decorators import login_required
from .models import *
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from Constraint.models import Constraint
from datetime import date,datetime
import hashlib
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q



def get_hash(string):
    hash_value = hashlib.sha256(string.encode()) 
    return hash_value.hexdigest()


def F(hash_value):
    last_char = hash_value[-1]
    new = hash_value[int(last_char,16):int(last_char,16)+7]
    otp = int(new,16)
    otp = int(str(otp)[0:4])
    return otp


def generate_OTP():
    hash_value = get_hash(str(datetime.now()))
    otp = F(hash_value)
    return otp


@login_required
def wallet_home(request):
    if request.user.is_authenticated:
        try:
            constraint = Constraint.objects.get(owner=request.user)
        except Constraint.DoesNotExist:
            return redirect('create_constraint')
        try:
            wallet = Wallet.objects.get(owner=request.user)
            transactions = Transaction.objects.filter(receiver=request.user)
            return render(request, 'Wallet/wallet_home.html',{'money':wallet.money,'transactions':transactions})
        except Wallet.DoesNotExist:
            return redirect('wallet_create') 
    else:   
        messages.success(request, f'log in first')
        return redirect('login')


class Wallet_Create(LoginRequiredMixin,CreateView):
    model = Wallet
    fields =[]
    template_name = 'Wallet/create_wallet.html'
    context_object_name = 'wallet'

    def form_valid(self,form):
        form.instance.owner = self.request.user
        if Wallet.objects.filter(owner=self.request.user).count() == 0:
        	return super().form_valid(form)
        else:
            return redirect('wallet_home')


def create_transcation_start(request):
    if request.user.is_authenticated:
        otp = generate_OTP()
        try:
            otp_object = OTP.objects.get(owner=request.user)
        except:
            otp_object = OTP.objects.create(owner=request.user)
        otp_object.otp = otp
        otp_object.date_posted = timezone.now()
        otp_object.save()
        send_mail(
                subject="Your OTP Password",
                message="Your OTP password is %s" % otp,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[request.user.email]
            )
        return redirect('transaction_create')
    else:
        messages.success(request, f'log in first')
        return redirect('login')

class Transaction_Create(LoginRequiredMixin,CreateView):
    model = Transaction
    fields = ['receiver','amount','otp']
    template_name = 'Wallet/create_transaction.html'
    context_object_name = 'transaction'

    def form_valid(self,form):
        otp_object = OTP.objects.get(owner=self.request.user)
        
        if form.instance.otp != otp_object.otp or otp_object.otp == -1:
            messages.success(self.request, f'OTP is incorrect or expired')
            return redirect('Wall-home')
        if (timezone.now()-otp_object.date_posted).total_seconds() > 300:
            messages.success(self.request, f'OTP is expired')
            return redirect('Wall-home')
        otp_object.otp = -1
        otp_object.save()

        form.instance.sender = self.request.user
        transactions = Transaction.objects.filter(sender=self.request.user)
        total_pending = 0
        for transaction in transactions:
            total_pending += int(transaction.amount)
        total_pending += int(form.instance.amount)

        constraint = Constraint.objects.get(owner=self.request.user)
        if constraint.user_type == 'casual':
            max_transaction = 15
        elif constraint.user_type == 'commercial':
            max_transaction = -1
        else:
            max_transaction = 30

        if max_transaction == -1:

            if Wallet.objects.get(owner = self.request.user).money >= int(total_pending) and int(form.instance.amount)>0:
                constraint.number_of_transactions+=1
                constraint.save()
                return super().form_valid(form)
            else:
                if int(form.instance.amount) < 0:
                    messages.success(self.request, f'Amount should be greater than 0')
                    return redirect('wallet_home')
                elif Wallet.objects.get(owner = self.request.user).money >= int(total_pending):
                    messages.success(self.request, f'the sum of your pending transactions is greater than your account balance')
                    return redirect('wallet_home')
                return redirect('wallet_home')
        else:
            if Wallet.objects.get(owner = self.request.user).money >= int(total_pending) and int(form.instance.amount)>0 and max_transaction>constraint.number_of_transactions:
                constraint.number_of_transactions+=1
                constraint.save()
                return super().form_valid(form)
            else:
                if int(form.instance.amount) < 0:
                    messages.success(self.request, f'Amount should be greater than 0')
                    return redirect('wallet_home')
                elif Wallet.objects.get(owner = self.request.user).money >= int(total_pending):
                    messages.success(self.request, f'the sum of your pending transactions is greater than your account balance')
                    return redirect('wallet_home')
                elif max_transaction < constraint.number_of_transactions:
                    messages.success(self.request, f'You have exceeded your transaction limit')
                    return redirect('wallet_home')
                return redirect('wallet_home')


def accept_transaction(request,pk):
    if request.user.is_authenticated:
        transaction = Transaction.objects.get(pk=pk)
        wallet_sender = Wallet.objects.get(owner=transaction.sender)
        wallet_receiver = Wallet.objects.get(owner=transaction.receiver)	

        if request.user == transaction.receiver:
            if wallet_sender.money >= int(transaction.amount):
                wallet_sender.money = wallet_sender.money - int(transaction.amount)
                wallet_receiver.money = wallet_receiver.money + int(transaction.amount)
                wallet_receiver.save()
                wallet_sender.save()
                Transaction_Log.objects.create(sender=transaction.sender,receiver=transaction.receiver,amount=transaction.amount)
                transaction.delete()
            else:
                messages.success(request, f'The sender doesnt have enough money')
                return redirect('wallet_home')
        return redirect('wallet_home')
    else:
        messages.success(request, f'Login first')
        return redirect('login')


class Add_Money_Transaction_Create(LoginRequiredMixin,CreateView):
    model = Add_Money_Transaction
    fields = ['amount']
    template_name = 'Wallet/create_add_money_transaction.html'
    context_object_name = 'add_money_transaction'

    def form_valid(self,form):
        form.instance.sender = self.request.user
        amount = int(form.instance.amount)
        if amount > 0:
        	wallet = Wallet.objects.get(owner=self.request.user)
        	wallet.money = wallet.money + amount
        	wallet.save()
        	return super().form_valid(form)
        else:
        	return redirect('wallet_home')

@login_required
def view_transaction_logs(request):
	if request.user.is_authenticated:
		logs = Transaction_Log.objects.filter(Q(sender=request.user) | Q(receiver=request.user))
		return render(request, 'Wallet/view_transaction_logs.html',{'logs':logs})
	else:
		messages.success(request, f'log in first')
		return redirect('login')