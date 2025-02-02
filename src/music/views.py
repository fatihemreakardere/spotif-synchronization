import requests
import time
from django.conf import settings
from urllib.parse import urlencode
from django.shortcuts import redirect, render
from django.http import HttpResponse, JsonResponse

def index(request):
    token = request.session.get('access_token')
    if not token:
        return redirect('spotify_login')
    return render(request, 'music/client.html', {'token': token})

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