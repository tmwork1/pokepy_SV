from pokepy.pokemon import *

# Pokemonクラスを継承
class MyPokemon(Pokemon):
    def __init__(self, name: str = 'ピカチュウ', use_template: bool = True):
        super().__init__(name, use_template)
    
    def apply_template(self):
        """デフォルトの型を設定する"""
        if self.name in Pokemon.home:
            self.nature = Pokemon.home[self.name]['nature'][0][0]
            self.org_ability = Pokemon.home[self.name]['ability'][0][0]
            self.Ttype = Pokemon.home[self.name]['Ttype'][0][0]
            self.moves = Pokemon.home[self.name]['move'][0][:4]

# ライブラリの初期化
MyPokemon.init(season=None)

name = 'ガチグマ(アカツキ)'
p = MyPokemon(name, use_template=True)

print('-'*50 + '\nインスタンス変数\n' + '-'*50)
print(f'名前\t{p.name}')
print(f'タイプ\t{p.types}')
print(f'体重\t{p.weight}')
print(f'性別\t{p.sex}')
print(f'レベル\t{p.level}')
print(f'性格\t{p.nature}')
print(f'元の／現在の特性\t{p.org_ability} / {p.ability}')
print(f'アイテム\t{p.item}')
print(f'テラスタイプ\t{p.Ttype}')
print(f'種族値\t{p.base}')
print(f'個体値\t{p.indiv}')
print(f'努力値\t{p.effort}')
print(f'ステータス\t{p.status}')
print(f'HP\t{p.hp} ({p.hp_ratio*100}%)')
print(f'わざ\t{p.moves}')
print(f'PP\t{p.pp}')
print(f'能力ランク\t{Pokemon.status_label} = {p.rank}')
#print(f'状態変化\t{p.condition}')

print('-'*50 + '\nランクマッチの使用率\n' + '-'*50)
print(Pokemon.home[name]['nature'])
print(Pokemon.home[name]['ability'])
print(Pokemon.home[name]['item'])
print(Pokemon.home[name]['Ttype'])
print(Pokemon.home[name]['move'])