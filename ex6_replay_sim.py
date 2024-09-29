from pokepy.pokemon import *

# ライブラリの初期化
Pokemon.init()

with open('log/random_3on3.json', encoding='utf-8') as fin:
    log = json.load(fin)
    
    # シードを指定してBattleインスタンスを生成
    battle = Battle(seed=log['seed'])

    # ポケモンを復元
    for player in range(2):
        for p in log[str(player)]:
            battle.selected[player].append(Pokemon())
            battle.selected[player][-1].__dict__ |= p
            battle.selected[player][-1].show()

    # コマンドに従ってターンを進める
    while (key := f'Turn{battle.turn}') in dict:
        # あらかじめ交代コマンドの履歴をセットしておく
        battle.reserved_change_commands = log[key]['change_command_history']

        # コマンドを指定してターンを進める
        battle.proceed(commands=log[key]['command'])

        # 行動した順にログ表示
        for player in battle.action_order:
            print(f'{player=}', battle.log[player], battle.damage_log[player])