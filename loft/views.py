from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.models import User, Group
from loft.models import Game, Developer, Player, Transaction
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from hashlib import md5


# Create your views here.

def index(request):
    if request.method == "GET":
        user = request.user
        if not request.user.is_authenticated:
            return redirect("loft:home")
        if user.groups.filter(name="developers").count() != 0:
            return redirect("loft:developer")
        transactions = Transaction.objects.filter(player=user.player.id)
        purchased_games = []
        for transaction in transactions:
            purchased_games.append(transaction.game)
    return render(request, "loft/index.html", {"user":user, "purchased_games":purchased_games})

def signup(request):
    if request.user.is_authenticated:
        return redirect("loft:index")
    return render(request, 'loft/signup.html')


def logout_view(request):
    logout(request)
    return redirect("loft:login")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("loft:index")
    return render(request, 'loft/login.html')

def login_user(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        if not username or not password:
            return render(request, "loft/login.html", {"error":"One of the fields was empty"})
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("loft:index")
        else:
            return render(request, "loft/login.html", {"error":"Wrong username or password"})
    else:
        return redirect("loft:index")



def home(request):
    if request.method =="GET":
        if request.user.is_authenticated:
            return redirect("loft:index")
        games = Game.objects.all()
        return render(request, "loft/home.html", {"games":games})
    else:
        return HttpResponse(status=500)

def create(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        developer = False
        try:
            if request.POST['developer']:
                developer = True
        except KeyError:
            developer = False
        if username is not None and email is not None and password is not None:
            if not username or not email or not password:
                return render(request, "loft/signup.html", {"error": "please fill in all required fields"})
            if User.objects.filter(username=username).exists():
                return render(request, "loft/signup.html", {"error": "Username already exists"})
            elif User.objects.filter(email=email).exists():
                return render(request, "loft/signup.html", {"error": "Email already exists"})
            user = User.objects.create_user(username, email, password)
            if developer:
                if Group.objects.filter(name="developers").exists():
                    dev_group = Group.objects.get(name="developers")
                else:
                    Group.objects.create(name='developers').save()
                    dev_group = group.objects.get(name='developers')
                dev_group.user_set.add(user)
                Developer.objects.create(user=user).save()
            else:
                Player.objects.create(user=user).save()
            user.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("loft:index")
    else:
        return redirect("loft:signup")

def catalog_view(request):
    if request.method == "GET":
        user = request.user
        if not user.is_authenticated:
            return redirect("loft:login")
        if user.groups.filter(name="developers").count() != 0:
            return redirect("loft:index")
        games = Game.objects.all()
        return render(request, "loft/catalog.html", {"games":games})
    else:
        return HttpResponse(status=500)


def game_info(request, game_id):
    # Selled ID: gameloft
    # Secret Key: 426d1e9d6216e1f4572ad1367f10afc7
    if request.method == "GET":
        user = request.user
        if not user.is_authenticated:
            return redirect("loft:login")
        if user.groups.filter(name="developers").count() !=0:
            return redirect("loft:index")
        game = get_object_or_404(Game, pk=game_id)
        secret_key = "426d1e9d6216e1f4572ad1367f10afc7"
        pid = "testsale"
        sid = "gameloft"
        amount = game.price
        success = "https://supergameloft.herokuapp.com/payment/success/?game_id={}".format(game_id)
        cancel = "https://supergameloft.herokuapp.com/payment/cancel"
        error = "https://supergameloft.herokuapp.com/payment/error"
        checksumstr = "pid={}&sid={}&amount={}&token={}".format(pid,sid,amount,secret_key)
        digest = md5(checksumstr.encode("ascii"))
        checksum = digest.hexdigest()
        url = "http://payments.webcourse.niksula.hut.fi/pay/"
        transaction = Transaction.objects.filter(player=user.player.id, game=game.id)
        if transaction.count() !=0:
            return render(request, "loft/index.html",{"error":"Game already is in catalog"})
        return render(request, "loft/game_info.html",{"game":game, "url":url, "pid":pid, "sid":sid, "amount":amount, "success":success, "cancel":cancel, "error":error, "checksum":checksum })
    else:
        return HttpResponse(status=500)


def payment_success(request):
    if request.method == "GET":
        user = request.user
        if not user.is_authenticated:
            return redirect("loft:login")
        if user.groups.filter(name="developers").count() != 0:
            return redirect("loft:index")
        game_id = request.GET["game_id"]
        game = get_object_or_404(Game, pk=game_id)
        secret_key = "426d1e9d6216e1f4572ad1367f10afc7"
        pid = request.GET["pid"]
        ref = request.GET["ref"]
        result = request.GET["result"]
        checksum = request.GET["checksum"]
        checksumstr = "pid={}&ref={}&result={}&token={}".format(pid, ref, result, secret_key)
        digest = md5(checksumstr.encode("ascii"))
        calculated_hash = digest.hexdigest()
        if calculated_hash == checksum:
            Transaction.objects.create(game=game, player=user.player, paid_amount=game.price).save()
            return redirect("loft:index")
        else:
            return HttpResponse(status=500)
    else:
        return HttpResponse(status=500)

def payment_cancel(request):
    if request.method == "GET":
        user = request.user
        if not user.is_authenticated:
            return redirect("loft:login")
        if user.groups.filter(name="developers").count() != 0:
            return redirect("loft:index")

        secret_key = "426d1e9d6216e1f4572ad1367f10afc7"
        pid = request.GET["pid"]
        ref = request.GET["ref"]
        result = request.GET["result"]
        checksum = request.GET["checksum"]
        checksumstr = "pid={}&ref={}&result={}&token={}".format(pid, ref, result, secret_key)
        digest = md5(checksumstr.encode("ascii"))
        calculated_hash = digest.hexdigest()
        if calculated_hash == checksum:
            return render(request, "loft/index.html",{"error":"payment is cancelled"})
        else:
            return HttpResponse(status=500)
    else:
        return HttpResponse(status=500)


def payment_error(request):
    pass


def play_game(request, game_id):
    if request.method == "GET":
        user = request.user
        if not user.is_authenticated:
            return redirect("loft:login")
        if user.groups.filter(name="developers").count() != 0:
            return redirect("loft:index")
        game = get_object_or_404(Game, pk=game_id)
        player = user.player
        transaction = Transaction.objects.filter(game=game_id, player=player.id)
        if transaction.count() != 0:
            return render(request, "loft/play_game.html", {"game":game})
        else:
            return HttpResponse(status=500)
    else:
        return HttpResponse_(status=500)


def developer_view(request):
    if request.method == "GET":
        user = request.user
        if not user.is_authenticated:
            return redirect("loft:login")
        if user.groups.filter(name="developers").count() !=0:
                games = Game.objects.filter(developer=user.developer.id)
                statistics = []
                for game in games:
                    transactions = Transaction.objects.filter(game=game.id)
                    for transaction in transactions:
                        statistics.append(transaction)
                return render(request, "loft/developer.html", {"statistics":statistics})
        else:
                return redirect("loft:index")


def search(request):
    if request.method == "POST":
        user = request.user
        if not user.is_authenticated:
            return HttpResponse(status=500)
        if user.groups.filter(name="developers").count() != 0:
            return HttpResponse(status=500)
            # the "q" below if found on the html template player_base.html
        query = request.POST["q"]
        if not query:
            return render(request, "loft/search_result.html", {"error":"Empty search"})
        games = Game.objects.filter(title__icontains=query)
        return render(request, "loft/search_result.html", {"games":games, "query":query})
    else:
        return HttpResponse(status=500)



def publish_page_view(request):
    if request.method == "GET":
        user = request.user
        if not user.is_authenticated:
            return redirect("loft:login")
        if user.groups.filter(name="developers").count() !=0:
            return render(request, "loft/publish_game_form.html")
        else:
            return redirect("loft:index")

def developer_games(request):
    if request.method == "GET":
        user = request.user
        if not user.is_authenticated:
            return redirect("loft:login")
        if user.groups.filter(name="developers").count() !=0:
            games = user.developer.game_set.all()
            return render(request, "loft/developer_games.html", {"games":games})
        else:
            return redirect("loft:index")

def edit_game(request, game_id):
    if request.method == "GET":
        user = request.user
        if not user.is_authenticated:
            return redirect("loft:login")
        if user.groups.filter(name="developers").count() == 0:
            return redirect("loft:index")
        game = get_object_or_404(Game, pk=game_id)
        if game.developer.user_id == user.id:
            return render(request, "loft/edit_game.html", {"game":game})
        else:
            return HttpResponse(status=500)
    else:
        return HttpResponse(status=500)


def purchased_games(request):
    pass


def create_game(request):
    if request.method == "POST":
        user = request.user
        if not user.is_authenticated:
            return HttpResponse(status=500)
        if user.groups.filter(name="developers").count() == 0:
            return HttpResponse(status=500)
        developer = user.developer
        title = request.POST["title"]
        price = request.POST["price"]
        url = request.POST["url"]
        if not title and not url and not price:
            return render(request, "loft/publish_game_form.html", {"error":"Please fill in all required fields"})
            #parse price to be FloatField
        try:
            float_price = float(price)
        except ValueError:
            return render(request, "loft/publish_game_form.html", {"error":"Price is not a number"})
        if float_price <= 0:
            return render(request, "loft/publish_game_form.html", {"error":"Price must be more than 0"})
        # Validate URL
        try:
            URLValidator()(url)
        except ValidationError:
            return render(request, "loft/publish_game_form.html", {"error":"URL is not valid"})
        try:
            Game.objects.create(title=title, price=float_price, url=url, developer=developer)
        except(ValidationError, IntegrityError) as e:
            return render(request, "loft/publish_game_form.html", {"error":"URL is not unique"})

        return redirect("loft:developer_games")
    else:
        return redirect("loft:signup")


def edit_game_update(request, game_id):
    if request.method == "POST":
        user = request.user
        if not user.is_authenticated:
            return HttpResponse(status=500)
        if user.groups.filter(name="developers").count() == 0:
            return HttpResponse(status=500)
        game = get_object_or_404(Game, pk=game_id)
        if game.developer.user_id == user.id:
            title = request.POST["title"]
            price = request.POST["price"]
            url = request.POST["url"]
            if not title and not price and not url:
                return render(request, "loft/edit_game.html", {"error": "At least one of the field must be filled",
                    "game":game})
            if title.strip():
                Game.objects.filter(pk=game_id).update(title=title)
            if price.strip():
                try:
                    float_price = float(price)
                except ValueError:
                    return render(request, "loft/edit_game.html",{"error": "Price is not number",
                        "game":game})
                if float_price <= 0:
                    return render(request, "loft/edit_game.html",{"error": "Price is negative",
                        "game":game})
                Game.objects.filter(pk=game_id).update(price=price)
            if url.strip():
                try:
                    URLValidator()(url)
                except ValidationError:
                    return render(request, "loft/edit_game.html",{"error": "URL is malformed",
                        "game":game})
                try:
                    Game.objects.filter(pk=game_id).update(url=url)
                except (ValidationError, IntegrityError) as e:
                    return render(request, "loft/edit_game.html",{"error": "URL is not unique",
                        "game":game})
            return redirect("loft:developer_games")
        else:
            return HttpResponse(status=500)
    else:
        return HttpResponse(status=500)





def edit_game_delete(request, game_id):
    if request.method == "POST":
        user = request.user
        if not user.is_authenticated:
            return HttpResponse(status=500)
        if user.groups.filter(name="developers").count() == 0:
            return HttpResponse(status=500)
        game = get_object_or_404(Game, pk=game_id)
        if game.developer.user_id == user.id:
            Game.objects.get(pk=game_id).delete()
            return redirect("loft:developer_games")
    else:
        return HttpResponse(status=500)



def facebook_handler(request):
    if request.method == "GET":
        user = request.user
        if Player.objects.filter(user=user).exists():
            return redirect("loft:index")
        else:
            Player.objects.create(user=user).save()
            player = Player.objects.filter(user=user)
            user = player
            return redirect("loft:index")
    else:
        return HttpResponse(status=500)
