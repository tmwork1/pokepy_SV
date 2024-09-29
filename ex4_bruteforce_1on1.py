from pokepy.pokemon import *

# Battleクラスを継承
class MyBattle(Battle):
    def __init__(self):
        super().__init__()

    def battle_command(self, player):
        """{player}のターン開始時に呼ばれる方策関数"""

        # プレイヤー視点の仮想盤面を生成
        blinded = self.clone(player)

        # 両プレイヤーの選択可能なコマンドの一覧を取得
        # 自分: player (= 0 or 1), 相手: not player (= 1 or 0)
        available_commands_list = [
            blinded.available_commands(pl) for pl in [player, not player]
        ]

        scores = []

        # 自分のコマンドのループ
        for c0 in available_commands_list[0]:
            _scores = []

            # 相手のコマンドのループ
            for c1 in available_commands_list[1]:
                
                # コマンドごとに仮想盤面を複製
                battle = deepcopy(blinded)

                # コマンドを指定して仮想盤面のターンを進める
                battle.proceed(commands=([c0, c1] if player == 0 else [c1, c0]))

                # 行動が有効なら盤面の評価値を計算し、無効なら0を記録する
                if battle.was_valid[player]:
                    _scores.append(battle.score(player))
                else:
                    _scores.append(0)

            # 相手のとりうる行動に対して最低スコアを記録
            scores.append(min(_scores))            

        # スコアが最も高いコマンドを選ぶ
        return available_commands_list[0][scores.index(max(scores))]
        
    def score(self, player: int) -> float:
        """盤面の評価値を返す"""
        # 例: TODスコアの比
        return (self.TOD_score(player) + 1e-3) / (self.TOD_score(not player) + 1e-3)


# ライブラリの初期化
Pokemon.init()

# Battleクラスのインスタンスを生成
battle = MyBattle()

# ポケモンを生成して選出に追加
battle.selected[0].append(Pokemon('サーフゴー'))
battle.selected[1].append(Pokemon('アシレーヌ'))

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