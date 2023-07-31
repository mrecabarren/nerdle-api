from django.db import models
from django.contrib.postgres.fields import ArrayField
import random


class Game(models.Model):
    start = models.DateTimeField()
    end = models.DateTimeField()

    eq_length = models.IntegerField(default=5)
    eq_count = models.IntegerField(default=1)
    operators = models.TextField(default='+-')
    equalities = ArrayField(models.TextField(blank=True, null=True), blank=True, null=True)
    resettable = models.BooleanField(default=True)

    created = models.DateTimeField(auto_now_add=True, blank=True)

    def __str__(self):
        return f'{self.id}: {self.operators} {self.eq_length} {len(self.equalities)} [{self.start}]'

    @property
    def short_name(self):
        return f'{self.id}:[{self.operators}] {self.eq_length}|{len(self.equalities)}'

    @property
    def join_equations(self):
        return ', '.join(self.equalities)

    @property
    def operators_list(self):
        return [o for o in self.operators]

    @property
    def valid_symbols(self):
        symbols = [str(d) for d in range(0, 10)]
        symbols.extend(self.operators_list)
        symbols.append('=')
        return symbols

    def to_dict(self):
        return {
            'id': self.id,
            'start': self.start,
            'end': self.end,
            'operators': self.operators,
            'eq_length': self.eq_length,
            'eq_count': self.eq_count
        }

    def check_equality(self, equality):
        # TODO: chequear que haya un igual, que se respete las operaciones, y que la igualdad sea válida
        if len(equality) != self.eq_length:  # length
            print('length')
            return False
        elif equality.count('=') != 1:  # una igualdad
            print('una igualdad')
            return False
        elif any([c not in self.valid_symbols for c in equality]):  # simbolos validos
            print(f'simbolos validos: {self.valid_symbols}')
            return False
        elif not equality[equality.find('=')+1:].lstrip('-').isnumeric():  # numero a la derecha
            print(f"numero a la derecha: {equality[equality.find('=')+1:]}")
            return False
        elif not self.__validate_equality(equality):  # igualdad valida
            print('igualdad valida')
            return False
        return True

    def evaluate(self, play):
        results = []
        for eq in self.equalities:
            r = self.__analyze_equality(play, eq)
            results.append("".join(r))

        return results

    def create_equalities(self):
        eqs = []
        for i in range(self.eq_count):
            operation = self.__operation_recursive()
            res = self.__resolve_operation(operation)
            eqs.append(f'{operation}={res}')

        self.equalities = eqs
        self.save()

    def __resolve_operation(self, operation):
        res = None
        try:
            # Siempre división entera
            operation = operation.replace('/', '//')
            # Reemplazar elevado
            operation = operation.replace('^', '**')
            res = eval(operation)
        except Exception as e:
            print(e)
        finally:
            return res

    def __validate_equality(self, equality):
        equals_pos = equality.find('=')
        if equals_pos == -1:  # No está el signo de igualdad
            return None

        op1 = equality[:equals_pos]
        op2 = equality[equals_pos + 1:]

        res_op1 = self.__resolve_operation(op1)
        res_op2 = self.__resolve_operation(op2)

        if res_op1 is not None and res_op2 is not None and res_op1 == res_op2:
            return True
        return False

    def __analyze_equality(self, play, equality):
        if self.__validate_equality(play):
            r = list('_' * len(equality))
            play_aux = list(play)
            equality_aux = list(equality)
            for pos, c in enumerate(play):
                if c == equality[pos]:
                    r[pos] = '2'
                    equality_aux[pos] = '_'
                    play_aux[pos] = '_'
            for pos, c in enumerate(play_aux):
                if c != '_':
                    if c in equality_aux and \
                            sum([1 if x == c else 0 for x in play_aux[:pos + 1]]) <= sum(
                            [1 if x == c else 0 for x in equality_aux]):
                        r[pos] = '1'
                    else:
                        r[pos] = '0'
            return r
        else:
            return None

    def __recursive_loop_digit(self, operation):
        next_0 = random.randint(0, 9)
        for i in range(0, 10):
            new_operation = f'{operation}{(next_0 + i) % 10}'
            op = self.__operation_recursive(new_operation)
            if op is not None:
                return op
        return None

    def __recursive_loop_operator(self, operation):
        next_0 = random.randint(0, len(self.operators_list) - 1)
        for i in range(0, len(self.operators_list)):
            next_d_0 = random.randint(0, 9)
            for j in range(0, 10):
                if self.operators_list[(next_0 + i) % len(self.operators_list)] not in ['/', '%'] or (next_d_0 + j) % 10 != 0:
                    new_operation = f'{operation}{self.operators_list[(next_0 + i) % len(self.operators_list)]}{(next_d_0 + j) % 10}'
                    op = self.__operation_recursive(new_operation)
                    if op is not None:
                        return op
        return None

    def __operation_recursive(self, operation=''):
        if len(operation) == 0:
            operation += str(random.randint(0, 9))
            return self.__operation_recursive(operation)
        else:
            res = str(self.__resolve_operation(operation))
            spaces_left = self.eq_length - (len(operation) + len(res) + 1)

            if spaces_left == 0:
                return operation
            elif spaces_left < 0 or (spaces_left == 1 and operation[-1] == '0'):
                return None
            elif spaces_left == 1:  # solo digito
                return self.__recursive_loop_digit(operation)
            elif operation[-1] == '0':  # después de un 0 viene operador
                return self.__recursive_loop_operator(operation)
            else:  # operacion o digito
                op_first = True if random.random() < 0.5 else False
                if op_first:
                    res_op = self.__recursive_loop_operator(operation)
                    if res_op is None:
                        res_op = self.__recursive_loop_digit(operation)
                    return res_op
                else:
                    res_op = self.__recursive_loop_digit(operation)
                    if res_op is None:
                        res_op = self.__recursive_loop_operator(operation)
                    return res_op


class Player(models.Model):
    name = models.CharField(max_length=200)
    key = models.CharField(max_length=10)
    play_count = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.name}'

    def last_valid_play(self, game):
        plays = Play.objects.filter(player=self.id,
                                    game=game,
                                    results__isnull=False,
                                    is_valid=True).order_by('-created').all()
        return plays[0] if len(plays) > 0 else None

    def game_plays_count(self, game):
        plays = Play.objects.filter(player=self.id,
                                    game=game,
                                    results__isnull=False,
                                    is_valid=True).order_by('-created').count()
        return plays

    def add_play(self):
        self.play_count += 1
        self.save()


class Play(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    equality = models.CharField(max_length=20, blank=True, null=True)
    is_valid = models.BooleanField(default=True)

    results = ArrayField(models.TextField(blank=True, null=True), blank=True, null=True)
    eqs_state = ArrayField(models.BooleanField(default=False), blank=True, null=True)

    finished = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True, blank=True)

    def __str__(self):
        return f'{self.player} - {self.game} - {self.created}'


class Tournament(models.Model):
    name = models.CharField(max_length=200)
    games = models.ManyToManyField(
        Game, blank=True, related_name='tournaments'
    )
    players = models.ManyToManyField(
        Player, blank=True, related_name='players'
    )

    def __str__(self):
        return f'{self.name} - {self.games_count} - {self.players_count}'

    @property
    def games_count(self):
        return self.games.count()

    @property
    def players_count(self):
        return self.players.count()


class GamesSummary(Game):
    class Meta:
        proxy = True
        verbose_name = 'Game Summary'
        verbose_name_plural = 'Games Summary'
