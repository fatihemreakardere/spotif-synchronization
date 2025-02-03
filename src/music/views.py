import requests
import time
from django.conf import settings
from urllib.parse import urlencode
from django.shortcuts import redirect, render
from django.http import HttpResponse, JsonResponse
import random
from django.views.decorators.http import require_POST
from .models import Party
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.utils.crypto import get_random_string  # added import

def index(request):
    token = request.session.get('access_token')
    party = None
    if request.user.is_authenticated:
        party = Party.objects.filter(participants=request.user).first()
    if not token:
        return redirect('spotify_login')
    return render(request, 'music/client.html', {'token': token, 'party': party})

def start_party(request):
    if not request.user.is_authenticated:
        # Create a Spotify base user automatically
        username = "spotify_user_" + str(random.randint(1000, 9999))
        password = get_random_string(12)  # replaced make_random_password()
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
    party_code = str(random.randint(100000, 999999))
    while Party.objects.filter(party_code=party_code).exists():
        party_code = str(random.randint(100000, 999999))
    party = Party.objects.create(party_code=party_code, host=request.user)
    party.participants.add(request.user)
    return redirect('index')

@require_POST
def join_party(request):
    if not request.user.is_authenticated:
        # Create a Spotify base user automatically
        username = "spotify_user_" + str(random.randint(1000, 9999))
        password = get_random_string(12)
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
    party_code = request.POST.get('party_code')
    try:
        party = Party.objects.get(party_code=party_code)
        party.participants.add(request.user)
    except Party.DoesNotExist:
        # Optionally handle wrong party code (e.g., add a message)
        pass
    return redirect('index')

@require_POST
def quit_party(request):
    if not request.user.is_authenticated:
        return redirect('index')
    try:
        # Assume a user is in at most one party
        party = Party.objects.filter(participants=request.user).first()
        if party:
            # If host, delete party
            if party.host == request.user:
                party.delete()
            else:
                party.participants.remove(request.user)
                if party.participants.count() == 0:
                    party.delete()
    except Party.DoesNotExist:
        pass
    return redirect('index')

@require_POST
def delete_party(request):
    if not request.user.is_authenticated:
        return redirect('index')
    # Delete all parties where the current user is the host to avoid MultipleObjectsReturned.
    Party.objects.filter(host=request.user).delete()
    return redirect('index')

def spotify_login(request):
    scope = "user-read-playback-state user-modify-playback-state streaming"
    params = {
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        "scope": scope,
    }
    url = "https://accounts.spotify.com/authorize?" + urlencode(params)
    return redirect(url)

def spotify_callback(request):
    # Handle Spotify's callback and exchange the authorization code for an access token.
    code = request.GET.get('code')
    error = request.GET.get('error')
    if error:
        return HttpResponse("Error: " + error)
    
    token_url = "https://accounts.spotify.com/api/token"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "client_secret": settings.SPOTIFY_CLIENT_SECRET,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(token_url, data=payload, headers=headers)
    if response.status_code != 200:
        return HttpResponse("Failed to get token from Spotify")
    
    token_info = response.json()
    # Save token info in the session
    request.session['access_token'] = token_info.get('access_token')
    request.session['refresh_token'] = token_info.get('refresh_token')
    request.session['expires_at'] = int(time.time()) + token_info.get('expires_in')
    
    return redirect('index')

def spotify_realtime_status(request):
    access_token = request.session.get('access_token')
    if not access_token:
        return HttpResponse("Unauthorized", status=401)
    headers = {
        "Authorization": "Bearer " + access_token
    }
    player_url = "https://api.spotify.com/v1/me/player"
    response = requests.get(player_url, headers=headers)
    if response.status_code != 200:
        return HttpResponse("Failed to get player status", status=response.status_code)
    return JsonResponse(response.json())