"""
対戦Botのサンプルスクリプト

スクリプト実行時の第一引数によって動作が変わる

    sudo python ex14_sample_bot.py 0 # 対人戦
    sudo python ex14_sample_bot.py 1 # 対NPC戦 (学校最強大会)
"""

from pokepy.pokebot import *
from distutils.util import strtobool
import random
import sys


# Pokebotクラスを継承
class MyBot(Pokebot):
    def __init__(self):
        super().__init__()

    def selection_command(self, player=0) -> list[int]:
        """{player}の選出画面で呼ばれる方策関数
            n=0~5 : パーティのn番目のポケモンを選出
            選出する順番に数字を格納したリストを返す
        """
        # ランダム選出
        return random.sample(
            list(range(len(self.party[player]))), 3
        )

    def battle_command(self, player):
        """{player}のターン開始時に呼ばれる方策関数
            ex4_bruteforce_1on1.py から流用
        """
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
            print(f'\tコマンド {c0}\tスコア {scores[-1]:.1f}\tあと{self.thinking_time():.1f}秒')

        # スコアが最も高いコマンドを選ぶ
        return available_commands_list[0][scores.index(max(scores))]
   
    def change_command(self, player: int) -> int:
        """{player}の任意交代時に呼ばれる方策関数"""
        # ランダム交代
        return random.choice(self.available_commands(player, phase='change'))

    def score(self, player: int) -> float:
        """盤面の評価値を返す"""
        # 例: TODスコアの比
        return (self.TOD_score(player) + 1e-3) / (self.TOD_score(not player) + 1e-3)


# ライブラリの初期化
Pokemon.init(season=None)

# Botを生成、実行
bot = MyBot()
bot.main_loop(vs_NPC=strtobool(sys.argv[1]))