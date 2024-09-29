from pokepy.pokemon import *

# ライブラリの初期化
Pokemon.init()

# Battleクラスのインスタンスを生成
battle = Battle()

# ポケモンを3匹ずつ生成して選出に追加
for player in range(2):
    names = random.sample(list(Pokemon.home.keys()), 3)
    print(f'{player=} の選出 {names}')

    for i in range(3):
        battle.selected[player].append(Pokemon(names[i]))

# 勝敗が決まるまで繰り返す
while battle.winner() is None:
    # ターン経過
    battle.proceed()

    # 行動した順にログ表示
    print(f'\nターン{battle.turn}')
    for player in battle.action_order:
        print(f'{player=}', battle.log[player], battle.damage_log[player])

    if battle.turn == 3:
        break

# ログファイルに書き出す
with open('log/random_3on3.json', 'w', encoding='utf-8') as fout:
    fout.write(battle.dump())
