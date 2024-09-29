from pokepy.pokemon import *

# Battleクラスを継承
class MyBattle(Battle):
    def __init__(self):
        super().__init__()

    def battle_command(self, player: int) -> int:
        """{player}のターン開始時に呼ばれる方策関数"""
        return self.available_commands(player)[0]
    
    def change_command(self, player: int) -> int:
        """{player}の任意交代時に呼ばれる方策関数"""

        # 選択可能なコマンドの一覧を取得
        available_commands = self.available_commands(player, phase='change')

        print('\t'+'-'*30 + ' 交代の方策関数 ' + '-'*30)
        print('\tここまでの展開')
        for pl in self.action_order:
            print(f'\t\tPlayer {pl} {self.log[pl]}')

        scores = []

        # 自分のコマンドのループ
        for cmd in available_commands:
            # コマンドごとに仮想盤面を生成
            battle = self.clone(player)

            # コマンドを指定して、交代の直前から仮想盤面を再開し、ターンの終わりまで進める
            battle.proceed(change_commands=[cmd, None] if player == 0 else [None, cmd])

            print(f'\tコマンド{cmd}を指定して仮想盤面を再開')
            print(f'\t\tPlayer {player} {battle.log[pl]}')

            # 交代後、さらにターンを進めることも可能
            #battle.proceed()
            
            # 盤面の評価値を記録
            scores.append(battle.score(player))

        print('\t'+'-'*76)

        # スコアが最も高いコマンドを返す
        return available_commands[scores.index(max(scores))]

    def score(self, player: int) -> float:
        """盤面の評価値を返す"""
        # 例: TODスコアの比
        return (self.TOD_score(player) + 1e-3) / (self.TOD_score(not player) + 1e-3)


# ライブラリの初期化
Pokemon.init()

# Battleクラスのインスタンスを生成
battle = MyBattle()

# ポケモンを生成して選出に追加
battle.selected[0].append(Pokemon('ママンボウ'))
battle.selected[0][-1].moves = ['クイックターン']
battle.selected[0].append(Pokemon('オーロンゲ'))
battle.selected[0].append(Pokemon('グライオン'))

battle.selected[1].append(Pokemon('カイリュー'))
battle.selected[1].append(Pokemon('ガチグマ(アカツキ)'))
battle.selected[1].append(Pokemon('サーフゴー'))

for player in range(2):
    battle.selected[player][-1].show()

# 勝敗が決まるまで繰り返す
while battle.winner() is None:
    # ターン経過
    battle.proceed()

    # 行動した順にログを表示
    print(f'\nターン{battle.turn}')
    for player in battle.action_order:
        print(f'{player=}', battle.log[player], battle.damage_log[player])

    if battle.turn > 0:
        break