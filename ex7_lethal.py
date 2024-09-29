from pokepy.pokemon import *

# ライブラリの初期化
Pokemon.init()

# ポケモンを生成
p1 = Pokemon('カイリュー', use_template=False)
#p1.nature = 'いじっぱり'
#p1.ability = ''
#p1.item = 'いのちのたま'
#p1.Ttype, p1.terastal = 'ステラ', True
#p1.rank = [0, 0, 0, 0, 0, 0]
#p1.ailment = 'BRN'
p1.show()

p2 = Pokemon('ガチグマ(アカツキ)', use_template=False)
#p2.nature = 'ずぶとい'
#p2.ability = ''
#p2.item = 'オボンのみ'
#p2.Ttype, p2.terastal = 'フェアリー', True
#p2.rank = [0, 0, 0, 0, 0, 0]
#p2.ailment = 'PSN'
#p2.condition['shiozuke'] = 1
p2.show()

# 攻撃側のプレイヤー
player = 0

# 攻撃技
move_list = ['スケイルショット']
#move_list = ['スケイルショット','じしん'] # 複数なら加算ダメ計
print(move_list)

n_hit = 5 # 連続技のヒット数

# Battleインスタンスを生成
battle = Battle()
battle.pokemon = [p1, p2]

# 盤面の状況を設定
#battle.condition['sandstorm'] = 1
#battle.condition['glassfield'] = 1
#battle.condition['reflector'] = [1, 1]

# 致死率計算
print(battle.lethal(move_list=move_list, player=player, n_hit=n_hit))

# ダメージ計算の詳細を表示
print(battle.damage_log[player])
