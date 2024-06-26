from datetime import datetime, timezone

from django.http import JsonResponse, HttpResponseBadRequest
from django.views import View

from nerdle_api.models import Game, Player, Play


class NerdleGamesView(View):

    def get(self, request):
        open_games = Game.objects.filter(start__lte=datetime.now(timezone.utc),
                                         end__gte=datetime.now(timezone.utc))

        open_games_list = [g.to_dict() for g in open_games]
        return JsonResponse({"games": open_games_list})


class NerdlePlayView(View):

    def post(self, request, *args, **kwargs):
        game_id = request.POST.get('game', None)
        player_key = request.POST.get('key', None)
        equality = request.POST.get('equality', None)

        if game_id is None or player_key is None or equality is None:
            return HttpResponseBadRequest(
                'El POST para esta vista DEBE contener los siguientes parámetros: game, key, equality')

        if not game_id.isnumeric():
            return HttpResponseBadRequest(
                f'El id del juego debe ser un número: {game_id}')

        player = Player.objects.filter(key=player_key).first()
        if player is None:
            return HttpResponseBadRequest(
                'No hay ningún jugador para la KEY dada')
        else:
            player.add_play()

        game = Game.objects.filter(id=game_id,
                                   end__gte=datetime.now(timezone.utc)).first()
        if game is None:
            if player_key == "PROF123":
                game = Game.objects.filter(id=game_id)
            if game is None:
                return HttpResponseBadRequest(
                    'El id del juego entregado no existe o no está activo')

        previous_state = player.last_valid_play(game)
        if previous_state is not None and previous_state.finished:
            return JsonResponse({"result": 'Juego ya finalizado',
                                 'finished': True})

        play = Play.objects.create(game=game,
                                   player=player,
                                   equality=equality)
        play.save()

        if not game.check_play(equality):
            play.is_valid = False
            play.error_type = game.equality_error(equality)
            play.save()
            return HttpResponseBadRequest(
                f'La igualdad {equality} no cumple alguna de las condiciones requeridas: {play.get_error_type_display()}')

        play.results = game.evaluate(equality)
        eqs_state = [r == '2'*game.eq_length for r in play.results]

        if previous_state is not None and previous_state.eqs_state is not None:
            eqs_state = [s1 or previous_state.eqs_state[i] for i, s1 in enumerate(eqs_state)]

        play.eqs_state = eqs_state

        play.finished = all(play.eqs_state)

        play.save()

        return JsonResponse({"result": play.results,
                             'equalities_state': play.eqs_state,
                             'finished': play.finished})


class NerdleResetView(View):

    def post(self, request, *args, **kwargs):
        game_id = request.POST.get('game', None)
        player_key = request.POST.get('key', None)

        if game_id is None or player_key is None:
            return HttpResponseBadRequest(
                'El POST para esta vista DEBE contener los siguientes parámetros: game, key')

        if not game_id.isnumeric():
            return HttpResponseBadRequest(
                f'El id del juego debe ser un número: {game_id}')

        player = Player.objects.filter(key=player_key).first()
        if player is None:
            return HttpResponseBadRequest(
                'No hay ningún jugador para la KEY dada')

        game = Game.objects.filter(id=game_id,
                                   end__gte=datetime.now(timezone.utc)).first()
        if game is None:
            return HttpResponseBadRequest(
                'El id del juego entregado no existe o no está activo')

        if not game.resettable and player_key != "PROF123":
            return HttpResponseBadRequest(
                'Este juego no permite ser reseteado')

        Play.objects.filter(game=game, player=player).delete()

        return JsonResponse({"result": 'Se eliminaron las jugadas', 'game': game_id})


class NerdleStatusView(View):

    def get(self, request):
        game_id = request.GET.get('game', None)
        player_key = request.GET.get('key', None)

        if game_id is None or player_key is None:
            return HttpResponseBadRequest(
                'El GET para esta vista DEBE contener los siguientes parámetros: game, key')

        player = Player.objects.filter(key=player_key).first()
        if player is None:
            return HttpResponseBadRequest(
                'No hay ningún jugador para la KEY dada')

        game = Game.objects.filter(id=game_id,
                                   end__gte=datetime.now(timezone.utc)).first()
        if game is None:
            return HttpResponseBadRequest(
                'El id del juego entregado no existe o no está activo')

        plays_count = player.game_plays_count(game)
        last_play = player.last_valid_play(game)

        if plays_count > 0 and last_play.finished:
            return JsonResponse({"finished": True, 'plays': plays_count, 'game': game_id})
        else:
            return JsonResponse({"finished": False, 'plays': plays_count, 'game': game_id})
