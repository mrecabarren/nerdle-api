import random

from django.contrib import admin

from nerdle_api.models import Game, Player, Play, Tournament, GamesSummary


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'play_count')


@admin.register(Play)
class PlayAdmin(admin.ModelAdmin):
    list_display = ('game', 'player', 'equality', 'is_valid', 'created', 'finished')
    list_filter = ('finished', 'game', 'player')


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('id', 'operators', 'eq_count', 'eq_length', 'join_equations', 'resettable', 'end')
    list_filter = ('tournaments',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.create_equalities()


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'games_count', 'players_count')


@admin.register(GamesSummary)
class GamesSummaryAdmin(admin.ModelAdmin):
    change_list_template = 'admin/games_summary.html'

    list_filter = ('tournaments',)

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context,
        )
        try:
            qs = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return response

        response.context_data['games'] = list(qs.order_by('id'))

        players = Player.objects.all().order_by('name')

        players_values = []
        for p in players:
            p_vals = {'name': p.name, 'games': []}
            p_sum = 0
            for g in qs.order_by('id'):
                p_plays = p.game_plays_count(g)
                p_sum += p_plays

                p_last = p.last_valid_play(g)

                p_vals['games'].append({'plays': p_plays,
                                        'finished': p_last.finished if p_last is not None else False})
            p_vals['total'] = p_sum
            p_vals['fs'] = len([g for g in p_vals['games'] if g['finished']])
            players_values.append(p_vals)

        players_values.sort(key=lambda x: (-x['fs'], x['total']))

        response.context_data['players_values'] = players_values

        return response
