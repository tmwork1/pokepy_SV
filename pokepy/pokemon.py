# -*- coding: utf-8 -*-
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN
import time
from datetime import datetime, timedelta, timezone
import json
from copy import deepcopy
import random
import warnings


def round_half_up(v: float) -> int:
    """四捨五入した値を返す"""
    return int(Decimal(str(v)).quantize(Decimal('0'),rounding=ROUND_HALF_UP))

def round_half_down(v: float) -> int:
    """五捨五超入した値を返す"""
    return int(Decimal(str(v)).quantize(Decimal('0'),rounding=ROUND_HALF_DOWN))

def push(dict: dict, key: str, value: int|float):
    """dictに要素を追加する。すでにkeyがある場合はvalueを加算する"""
    if key not in dict:
        dict[key] = value
    else:
        dict[key] += value

def zero_ratio(dict: dict) -> float:
    """keyがゼロのvalueを全valueの合計値で割った値を返す"""
    n, n0 = 0, 0
    for key in dict:
        n += dict[key]
        if float(key) == 0:
            n0 += dict[key]
    return n0/n

def offset_hp_keys(hp_dict: dict, v: int) -> dict:
    """hp dictのすべてのkeyにvを加算したdictを返す"""
    result = {}
    for hp in hp_dict:
        h = int(float(hp))
        new_hp = '0' if h == 0 else str(max(0, h+v))
        if new_hp != '0' and hp[-2:] == '.0':
            new_hp += '.0'
        push(result, new_hp, hp_dict[hp])
    return result

def to_hankaku(text: str) -> str:
    """全角英数字を半角に変換した文字列を返す"""
    return text.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)})).replace('・','･')

def average(ls: list[float]) -> float:
    return sum(ls)/len(ls)

def frac(v: float) -> float:
    return v - int(v)

class Pokemon:
    """
    ポケモンの個体を表現するクラス。ポケモンのデータ全般をクラス変数に持つ。
    
    クラス変数 (抜粋)
    ----------------------------------------
    Pokemon.zukan: dict
        key: ポケモン名。
        value: タイプ、特性、種族値、ゲーム上の表示名、体重。
        (例)
        Pokemon.zukan['オーガポン(かまど)'] = {
            'type': ['くさ', 'ほのお'],
            'ability': ['かたやぶり'],
            'base': [80, 120, 84, 60, 96, 110],
            'display_name': 'オーガポン',
            'weight': 39.8
        }

    Pokemon.zukan_name: dict
        key: ゲーム上の表示名。
        value: ポケモン名のリスト。
        (例)
        Pokemon.zukan_name['ウーラオス'] = ['ウーラオス(れんげき)', 'ウーラオス(いちげき)']
    
    Pokemon.home: dict
        key: ポケモン名。
        value: ランクマッチの使用率データ。
        (例)
        Pokemon.home['カイリュー'] = {
            'move': [['しんそく', 'じしん', 'りゅうのまい', 'はねやすめ', 'げきりん', 'スケイルショット', 'アンコール', 'アイアンヘッド', 'けたぐり', 'でんじは'],
                    [78.7, 78.0, 42.5, 39.4, 30.8, 24.5, 23.3, 16.2, 10.0, 9.9]],
            'ability': [['マルチスケイル', 'せいしんりょく'],
                    [99.8, 0.2]],
            'item': [['こだわりハチマキ', 'いかさまダイス', 'ゴツゴツメット', 'たべのこし', 'あつぞこブーツ', 'じゃくてんほけん', 'とつげきチョッキ', 'ラムのみ', 'シルクのスカーフ', 'おんみつマント'],
                    [33.9, 21.5, 18.3, 8.0, 4.3, 3.4, 2.2, 1.9, 1.7, 1.6]],
            'Ttype': [['ノーマル', 'じめん', 'はがね', 'ひこう', 'フェアリー', 'ほのお', 'でんき', 'みず', 'どく', 'ドラゴン'],
                    [65.0, 11.3, 11.0, 4.7, 4.5, 1.2, 0.7, 0.6, 0.4, 0.2]]
        }

    Pokemon.nature_corrections: dict
        key: 性格。
        value: 性格補正値リスト。
        (例)
        Pokemon.nature_corrections['いじっぱり'] = [1.0, 1.1, 1.0, 0.9, 1.0, 1.0]

    Pokemon.type_id = {
        'ノーマル': 0, 'ほのお': 1, 'みず': 2, 'でんき': 3, 'くさ': 4, 'こおり': 5, 'かくとう': 6,
        'どく': 7, 'じめん': 8, 'ひこう': 9, 'エスパー': 10, 'むし': 11, 'いわ': 12, 'ゴースト': 13,
        'ドラゴン': 14, 'あく': 15, 'はがね': 16, 'フェアリー': 17, 'ステラ': 18
    }

    Pokemon.type_corrections: list
        (例) どくタイプの技でくさおタイプに攻撃したときのタイプ補正値。
        Pokemon.type_corrections[7][4] = 2.0
    
    Pokemon.abilities: list[str]
        全ての特性。
    
    Pokemon.items: dict
        key: アイテム名。
        value: なげつける威力。
 
    Pokemon.all_moves: dict
        key: わざ名。
        value: わざのタイプ、分類、威力、命中率、PP。
        (例)
        Pokemon.all_moves['しんそく'] = {
            'type': 'ノーマル',
            'class': 'phy',
            'power': 80,
            'hit': 100,
            'pp': 8
        }

    Pokemon.combo_hit: dict
        key: 連続技。
        value: [最小ヒット数, 最大ヒット数]。
        
    インスタンス変数 (抜粋)
    ----------------------------------------
    self.__name: str
        ポケモン名。
    
    self.__display_name: str
        ゲーム上の表示名。
    
    self.__types: list[str]
        タイプ。
    
    self.__weight: float
        体重。
    
    self.sex: int
        性別。Pokemon.MALE or Pokemon.FEMALE or Pokemon.NONSEXUAL。
    
    self.__level: int
        レベル。
    
    self.__nature: str
        性格。
    
    self.__org_ability: str
        もとの特性。
    
    self.ability: str
        現在の特性。試合中に技や特性により変更される可能性がある。
    
    self.item: str
        所持しているアイテム。
    
    self.lost_item: str
        失ったアイテム。
    
    self.Ttype: str
        テラスタイプ。
    
    self.terastal: bool
        テラスタルしていればTrue。

    self.__status: list[int]
        ステータス。[H,A,B,C,D,S]。

    self.__base: list[int]
        種族値。[H,A,B,C,D,S]。

    self.__indiv: list[int]
        個体値。[H,A,B,C,D,S]。

    self.__effort: list[int]
        努力値。[H,A,B,C,D,S]。

    self.__hp: int
        残りHP。

    self.__hp_ratio: float
        残りHP割合。

    self.sub_hp: int
        みがわりの残りHP。

    self.__moves: list[str]
        わざ。最大10個。

    self.last_pp_move: str
        最後にPPを消費した技。
    
    self.last_used_move: str
        最後に出た技。
    
    self.pp: list[int]
        わざの残りPP。

    self.rank: list[int]
        能力ランク。[H,A,B,C,D,S,命中,回避]。
    
    self.ailment: str
        状態異常。

    self.condition: dict
        状態変化。

    self.boost_index: int
        クォークチャージ、こだいかっせい、ブーストエナジーにより上昇した能力番号。
    """

    zukan = {}
    zukan_name = {}
    form_diff = {}              # {表示名: フォルム差 (='type' or 'ability')}
    japanese_display_name = {}  # {各言語の表示名: 日本語の表示名}
    foreign_display_names = {}  # {日本語の表示名: [全言語の表示名]}
    home = {}

    type_file_code = {}         # {テラスタイプ: 画像コード}
    template_file_code = {}     # {ポケモン名: テンプレート画像コード}
    
    nature_corrections = {}
    type_id = {}
    type_corrections = []

    abilities = []
    ability_category = {}       # {分類: [該当する特性]}

    items = {}
    item_buff_type = {}         # {タイプ強化アイテム: 強化タイプ}
    item_debuff_type = {}       # {タイプ半減きのみ: 半減タイプ}
    item_correction = {}        # {アイテム: 威力補正}
    consumable_items = []       # 消耗アイテム

    all_moves = {}
    move_category = {}          # {分類: [該当する技]}
    move_value = {}             # {分類: {技: 値}}
    move_priority = {}          # {技: 優先度}
    combo_hit = {}
    move_effect = {}            # {技: 追加効果dict}
    
    stone_weather = {'sunny':'あついいわ','rainy':'しめったいわ','snow':'つめたいいわ','sandstorm':'さらさらいわ'}
    plate_type = {
        'まっさらプレート':'ノーマル','ひのたまプレート':'ほのお','しずくプレート':'みず','みどりのプレート':'くさ','いかずちプレート':'でんき','つららのプレート':'こおり',
        'こぶしのプレート':'かくとう','もうどくプレート':'どく','だいちのプレート':'じめん','あおぞらプレート':'ひこう','ふしぎのプレート':'エスパー','たまむしプレート':'むし',
        'がんせきプレート':'いわ','もののけプレート':'ゴースト','りゅうのプレート':'ドラゴン','こわもてプレート':'あく','こうてつプレート':'はがね','せいれいプレート':'フェアリー',
    }

    ailments = ('PSN', 'PAR', 'BRN', 'SLP', 'FLZ')
    weathers = ('sunny', 'rainy', 'snow', 'sandstorm')
    fields = ('elecfield', 'glassfield', 'psycofield', 'mistfield')
    
    # 性別
    MALE = 1
    FEMALE = -1
    NONSEXUAL = 0

    status_label = ('H', 'A', 'B', 'C', 'D', 'S', '命中', '回避')
    status_label_hiragana = ['HP','こうげき','ぼうぎょ','とくこう','とくぼう','すばやさ','めいちゅう','かいひ']
    status_label_kanji = ['HP','攻撃','防御','特攻','特防','素早さ','命中','回避']

    JPN = {
        'PSN':'どく', 'PAR':'まひ', 'BRN':'やけど', 'SLP':'ねむり', 'FLZ':'こおり',
        'confusion':'こんらん', 'critical':'急所ランク', 'aquaring':'アクアリング', 'healblock':'かいふくふうじ',
        'magnetrise':'でんじふゆう', 'noroi':'呪い', 'horobi':'ほろびのうた', 'yadorigi':'やどりぎのタネ',
        'ame_mamire':'あめまみれ', 'encore':'アンコール', 'anti_air':'うちおとす', 'kanashibari':'かなしばり',
        'shiozuke':'しおづけ', 'jigokuzuki':'じごくづき', 'charge':'じゅうでん', 'stock':'たくわえる',
        'chohatsu':'ちょうはつ', 'change_block':'にげられない', 'nemuke':'ねむけ', 'neoharu':'ねをはる',
        'bind':'バインド', 'meromero':'メロメロ', 'badpoison':'もうどく',
        'sunny':'はれ', 'rainy':'あめ', 'snow':'ゆき', 'sandstorm':'すなあらし',
        'elecfield':'エレキフィールド', 'glassfield':'グラスフィールド', 'psycofield':'サイコフィールド', 'mistfield':'ミストフィールド',
        'gravity': 'じゅうりょく', 'trickroom': 'トリックルーム', 'reflector': 'リフレクター', 'lightwall': 'ひかりのかべ',
        'oikaze': 'おいかぜ', 'safeguard': 'しんぴのまもり', 'whitemist': 'しろいきり', 'makibishi': 'まきびし', 'dokubishi': 'どくびし',
        'stealthrock': 'ステルスロック', 'nebanet': 'ねばねばネット', 'wish': 'ねがいごと',
    }

    def __init__(self, name: str='ピカチュウ', use_template:bool=True):
        """{name}のポケモンを生成する。{use_template}=Trueならテンプレートを適用して初期化する"""
        self.sex = Pokemon.NONSEXUAL
        self.__level = 50
        self.__nature = 'まじめ'
        if name in Pokemon.home:
            self.org_ability = Pokemon.home[name]['ability'][0][0]
        else:
            self.org_ability = Pokemon.zukan[name]['ability'][0]
        self.item = ''
        self.lost_item = ''

        self.__status = [0]*6
        self.__indiv = [31]*6
        self.__effort = [0]*6
        self.__hp = 0
        self.__hp_ratio = 1

        self.name = name
        self.Ttype = self.__types[0]

        self.__moves = []
        self.reset_game()

        if use_template:
            self.apply_template()

    def reset_game(self):
        """ポケモンを試合開始前の状態に初期化する"""
        self.come_back()
        self.ailment = ''
        self.terastal = False
        self.__hp = self.__status[0]
        self.__hp_ratio = 1
        self.pp = [Pokemon.all_moves[m]['pp'] if m else 0 for m in self.__moves]
        self.sleep_count = 0            # ねむり状態の残りターン
        
        # ばけのかわリセット
        if 'ばけのかわ' in self.ability:
            self.ability = self.__org_ability

        # おもかげやどし解除
        if 'オーガポン' in self.name:
            self.org_ability = Pokemon.zukan[self.name]['ability'][0]
        
        # フォルムリセット
        if self.name == 'イルカマン(マイティ)':
            self.name == 'イルカマン(ナイーブ)'
            self.update_status()

        if self.name == 'テラパゴス(ステラ)':
            self.name = 'テラパゴス(テラスタル)'
            self.org_ability = 'テラスシェル'
            self.update_status()

    def come_back(self):
        """ポケモンを控えに戻したときの状態に初期化する"""
        self.rank = [0]*8
        self.last_pp_move = ''
        self.last_used_move = ''
        self.inaccessible = 0
        self.lockon = False
        self.lost_types = []
        self.added_types = []
        self.sub_hp = 0
        self.boost_index = 0
        self.acted_turn = 0                 # 行動したターン数
        self.n_attacked = 0                 # 被弾回数
        self.fixed_move = ''                # こだわっている技
        self.hide_move = ''                 # 隠れている技(を使っている状態)
        self.BE_activated = False           # ブーストエナジーが発動していればTrue
        self.rank_dropped = False           # ランク下降していればTrue
        self.berserk_triggered = False      # ぎゃくじょうの発動条件を満たしていればTrue
        
        self.condition = {
            'confusion': 0,     # こんらん 残りターン
            'critical': 0,      # 急所ランク上昇
            'aquaring': 0,      # アクアリング
            'healblock': 0,     # かいふくふうじ 残りターン
            'magnetrise': 0,    # でんじふゆう 残りターン
            'noroi': 0,         # のろい
            'horobi': 0,        # ほろびのうたカウント
            'yadorigi': 0,      # やどりぎのタネ

            # 以上がバトンタッチ対象

            'ame_mamire': 0,    # あめまみれ 残りターン
            'encore': 0,        # アンコール 残りターン
            'anti_air': 0,      # うちおとす
            'kanashibari': 0,   # かなしばり 残りターン
            'shiozuke': 0,      # しおづけ
            'jigokuzuki': 0,    # じごくづき 残りターン
            'charge': 0,        # じゅうでん
            'stock': 0,         # たくわえるカウント
            'chohatsu': 0,      # ちょうはつ 残りターン
            'change_block': 0,  # にげられない
            'nemuke': 0,        # ねむけ 残りターン
            'neoharu': 0,       # ねをはる
            'michizure': 0,     # みちづれ
            'meromero': 0,      # メロメロ
            'badpoison': 0,     # もうどくカウント
            'bind': 0,          # バインド (残りターン)+0.1*(ダメージ割合)
        }

        # 特性の処理
        if self.ability == 'さいせいりょく' and self.condition['healblock'] == 0:
            self.hp = min(self.__status[0], self.hp + int(self.__status[0]/3))
        elif self.ability == 'しぜんかいふく':
            self.ailment = ''

        if 'ばけのかわ' not in self.ability:
            self.ability = self.__org_ability


    def update_status(self, keep_damage=False):
        """ステータスを更新する。
        {keep_damage}=Trueならステータス更新前に受けていたダメージを更新後にも適用し、FalseならHPを全回復する。
        """
        nc = Pokemon.nature_corrections[self.__nature]
        damage = self.__status[0] - self.__hp

        self.__status[0] = int((self.base[0]*2+self.__indiv[0]+int(self.__effort[0]/4))*self.__level/100)+self.__level+10
        for i in range(1,6):
            self.__status[i] = int((int((self.base[i]*2+self.__indiv[i]+int(self.__effort[i]/4))*self.__level/100)+5)*nc[i])

        self.hp = int(self.__status[0] * self.__hp_ratio)
        if keep_damage:
            self.hp = self.hp - damage

    def apply_template(self):
        """ポケモンの型を設定する"""
        if self.__name in Pokemon.home:
            self.__nature = Pokemon.home[self.__name]['nature'][0][0]
            self.org_ability = Pokemon.home[self.__name]['ability'][0][0]
            self.Ttype = Pokemon.home[self.__name]['Ttype'][0][0]
            self.moves = Pokemon.home[self.__name]['move'][0][:4]

    # Getter
    @property
    def name(self):
        return self.__name

    @property
    def display_name(self):
        return self.__display_name

    @property
    def level(self):
        return self.__level

    @property
    def weight(self):
        w = self.__weight
        match self.ability:
            case 'ライトメタル':
                w = int(w*0.5*10)/10
            case 'ヘヴィメタル':
                w *= 2
        if self.item == 'かるいし':
            w = int(w*0.5*10)/10
        return w
    
    @property
    def nature(self):
        return self.__nature

    @property
    def types(self):
        result = self.__types.copy()
        if self.terastal:
            if self.Ttype != 'ステラ':
                result = [self.Ttype]
        else:
            if self.__name == 'アルセウス':
                result = [Pokemon.plate_type[self.item] if self.item in Pokemon.plate_type else 'ノーマル']
            else:
                result = [t for t in result if t not in self.lost_types]
                result += self.added_types
        return result

    @property
    def org_types(self):
        return self.__types.copy()
    
    @property
    def org_ability(self):
        return self.__org_ability

    @property
    def status(self):
        return self.__status.copy()

    @property
    def base(self):
        return self.__base.copy()

    @property
    def indiv(self):
        return self.__indiv.copy()

    @property
    def effort(self):
        return self.__effort.copy()

    @property
    def moves(self):
        return self.__moves.copy()

    @property
    def hp(self):
        return self.__hp

    @property
    def hp_ratio(self):
        return self.__hp_ratio

    # Setter
    @name.setter
    def name(self, name: str):
        if name not in Pokemon.zukan:
            warnings.warn(f'{name} is not in Pokemon.zukan')
        else:
            self.__name = name
            self.__display_name = Pokemon.zukan[self.__name]['display_name']
            self.__types = Pokemon.zukan[self.__name]['type'].copy()
            self.__base = Pokemon.zukan[self.__name]['base'].copy()
            self.__weight = Pokemon.zukan[self.__name]['weight']
            self.update_status()

    def change_form(self, name: str):
        if name not in Pokemon.zukan:
            warnings.warn(f'{name} is not in Pokemon.zukan')
        else:
            self.__name = name
            self.__display_name = Pokemon.zukan[self.__name]['display_name']
            self.__types = Pokemon.zukan[self.__name]['type'].copy()
            self.__base = Pokemon.zukan[self.__name]['base'].copy()
            self.__weight = Pokemon.zukan[self.__name]['weight']
            self.update_status(keep_damage=True)

            if self.__name == 'ザシアン(けんのおう)' and 'アイアンヘッド' in self.__moves:
                ind = self.__moves.index('アイアンヘッド')
                self.set_move(ind, 'きょじゅうざん')

            if self.__name == 'ザマゼンタ(たてのおう)' and 'アイアンヘッド' in self.__moves:
                ind = self.__moves.index('アイアンヘッド')
                self.set_move(ind, 'きょじゅうだん')

    @level.setter
    def level(self, level: int):
        self.__level = level
        self.update_status()

    @nature.setter
    def nature(self, nature: str):
        self.__nature = nature
        self.update_status()

    @org_ability.setter
    def org_ability(self, ability: str):
        self.__org_ability = self.ability = ability

    @status.setter
    def status(self, status: list[int]):
        nc = Pokemon.nature_corrections[self.__nature]
        for i in range(6):
            for eff in range(0,256,4):
                if i == 0:
                    v = int((self.__base[0]*2+self.__indiv[0]+int(eff/4))*self.__level/100)+self.__level+10
                else:
                    v = int((int((self.__base[i]*2+self.__indiv[i]+int(eff/4))*self.__level/100)+5)*nc[i])
                if v == status[i]:
                    self.__effort[i] = eff
                    self.__status[i] = v
                    break
    
    def set_status(self, index: int, value: int) -> bool:
        nc = Pokemon.nature_corrections[self.__nature]
        for eff in range(0,256,4):
            if index == 0:
                v = int((self.__base[0]*2+self.__indiv[0]+int(eff/4))*self.__level/100)+self.__level+10
            else:
                v = int((int((self.__base[index]*2+self.__indiv[index]+int(eff/4))*self.__level/100)+5)*nc[index])
            if v == value:
                self.__effort[index] = eff
                self.__status[index] = v
                return True
        return False

    @indiv.setter
    def indiv(self, indiv: list[int]):
        self.__indiv = indiv
        self.update_status()

    @effort.setter
    def effort(self, effort: list[int]):
        self.__effort = effort
        self.update_status()

    def set_effort(self, index: int, value: list[int]):
        self.__effort[index] = value
        self.update_status()

    @moves.setter
    def moves(self, moves: list[str]):
        self.__moves, self.pp = [], []
        for move in moves:
            if not move or move in self.__moves:
                continue
            elif move not in Pokemon.all_moves:
                warnings.warn(f'{move} is not in Pokemon.all_moves')
            else:
                self.__moves.append(move)
                self.pp.append(Pokemon.all_moves[move]['pp'])

            if len(self.__moves) == 10:
                break

    def set_move(self, index: int, move: str):
        """技を追加してPPを初期化する"""
        if index not in range(10) or not move or move in self.__moves:
            return
        elif move not in Pokemon.all_moves:
            warnings.warn(f'{move} is not in Pokemon.all_moves')
        else:
            self.__moves[index] = move
            self.pp[index] = Pokemon.all_moves[move]['pp']

    def add_move(self, move: str):
        """技を追加してPPを初期化する"""
        if not move or move in self.__moves or len(self.__moves) == 10:
            return
        elif move not in Pokemon.all_moves:
            warnings.warn(f'{move} is not in Pokemon.all_moves')
        else:
            self.__moves.append(move)
            self.pp.append(Pokemon.all_moves[move]['pp'])

    @hp.setter
    def hp(self, hp: int):
        self.__hp = hp
        self.__hp_ratio = self.__hp / self.__status[0]

    @hp_ratio.setter
    def hp_ratio(self, hp_ratio: int):
        self.__hp_ratio = hp_ratio
        self.__hp = int(hp_ratio * self.__status[0])
        if hp_ratio and self.__hp == 0:
            self.__hp = 1

    def use_terastal(self) -> bool:
        if self.terastal:
            return False
        
        self.terastal = True

        if 'オーガポン' in self.name:
            self.org_ability = 'おもかげやどし'
        elif 'テラパゴス' in self.name:
            self.change_form('テラパゴス(ステラ)')

        return True

    def has_protected_ability(self) -> bool:
        """特性が上書きされない状態ならTrueを返す"""
        return self.ability in Pokemon.ability_category['protected'] or self.item == 'とくせいガード'

    def is_blowable(self) -> bool:
        """強制交代されうる状態ならTrueを返す"""
        return self.ability not in ['きゅうばん','ばんけん'] and not self.condition['neoharu']

    def contacts(self, move: str) -> bool:
        """{move}を使用したときに直接攻撃ならTrueを返す"""
        return move in Pokemon.move_category['contact'] and \
            self.ability != 'えんかく' and self.item != 'ぼうごパッド' and \
            not (move in Pokemon.move_category['punch'] and self.item == 'パンチグローブ')

    def item_removable(self):
        """アイテムを奪われない状態ならTrueを返す"""
        if self.ability == 'ねんちゃく' or self.item == 'ブーストエナジー' or \
            'オーガポン(' in self.__name or \
            ('ザシアン' in self.__name and self.item == 'くちたけん') or \
            ('ザマゼンタ' in self.__name and self.item == 'くちたたて') or \
            ('ディアルガ' in self.__name and 'こんごうだま' in self.item) or \
            ('パルキア' in self.__name and 'しらたま' in self.item) or \
            ('ギラティナ' in self.__name and 'はっきんだま' in self.item) or \
            (self.__name == 'アルセウス' and 'プレート' in self.item) or \
            (self.__name == 'ゲノセクト' and 'カセット' in self.item):
            return False
        return True

    def show(self):
        print(f'\tName      {self.__name}')
        print(f'\tNature    {self.__nature}')
        print(f'\tAbility   {self.ability}')
        print(f'\tItem      {self.item} ({self.lost_item})')
        print(f'\tTerastal  {self.Ttype} {self.terastal}')
        print(f'\tMoves     {self.__moves}')
        print(f'\tEffort    {self.__effort}')
        print(f'\tStatus    {self.__status}')
        print(f'\tHP        {self.hp}')
        print()

    def rank_correction(self, index: int) -> float:
        """ランク補正値を返す。
        Parameters
        ----------
        index: int
            0,1,2,3,4,5,6,7
            H,A,B,C,D,S,命中,回避
        """
        if self.rank[index] >= 0:
            return (self.rank[index]+2)/2
        else:
            return 2/(2-self.rank[index])

    def move_class(self, move: str) -> str:
        """{move}を使用したときの技の分類を返す"""
        if move in ['テラバースト','テラクラスター'] and self.terastal:
            effA = self.__status[1]*self.rank_correction(1)
            effC = self.__status[3]*self.rank_correction(3)
            return 'phy' if effA >= effC else 'spe'
        return Pokemon.all_moves[move]['class']

    def last_pp_move_index(self) -> int:
        """最後にPPを消費した技のindexを返す"""
        return self.__moves.index(self.last_pp_move) if self.last_pp_move and \
            self.last_pp_move in self.__moves else None

    def energy_boost(self, boost: bool=True):
        """{boost}=Trueならブーストエナジーにより能力を上昇させ、Falseなら元に戻す"""
        if boost:
            ls = [v*self.rank_correction(i) for i,v in enumerate(self.__status[1:])]
            self.boost_index = ls.index(max(ls)) + 1
        else:
            self.boost_index = 0

    def fruit_recovery(self, hp_dict: dict) -> dict:
        """きのみによる回復後のHP dictを返す。リーサル計算用の関数"""
        result = {}
        for hp in hp_dict:
            if hp == '0' or hp[-2:] == '.0':
                push(result, hp, hp_dict[hp])
            elif self.item in ['オレンのみ','オボンのみ']:
                if float(hp) <= 0.5*self.__status[0]:
                    recovery = int(self.__status[0]/4) if self.item == 'オボンのみ' else 10
                    key = str(min(self.hp, int(float(hp)) + recovery)) + '.0'
                    push(result, key, hp_dict[hp])
                else:
                    push(result, hp, hp_dict[hp])
            elif self.item in ['フィラのみ','ウイのみ','マゴのみ','バンジのみ','イアのみ']:
                if float(hp)/self.__status[0] <= (0.5 if self.ability == 'くいしんぼう' else 0.25):
                    key = str(int(float(hp)) + int(self.__status[0]/3)) + '.0'
                    push(result, key, hp_dict[hp])
                else:
                    push(result, hp, hp_dict[hp])
        return result

    def damage_text(self, damage: dict, lethal_num: int, lethal_prob: float) -> str:
        """ リーサル計算結果から 'd1~d2 (p1~p2 %) 確n' 形式の文字列を生成する"""
        damages = [int(k) for k in list(damage.keys())]
        min_damage, max_damage = min(damages), max(damages)
        
        result = f'{min_damage}~{max_damage} ({100*min_damage/self.__status[0]:.1f}~{100*max_damage/self.__status[0]:.1f}%)'
        if lethal_prob == 1:
            result += f' 確{lethal_num}'
        elif lethal_prob > 0:
            result += f' 乱{lethal_num}({100*lethal_prob:.2f}%)'
        return result

    def find(pokemon_list, name: str='', display_name: str=''):
        """{pokemon_list}から条件に合致したPokemonインスタンスを返す"""
        for p in pokemon_list:
            if name == p.name or display_name == p.display_name:
                return p

    def index(pokemon_list, name: str='', display_name: str=''):
        """{pokemon_list}から条件に合致したPokemonインスタンスのindexを返す"""
        for i,p in enumerate(pokemon_list):
            if name == p.name or display_name == p.display_name:
                return i
            
    def rank2str(rank_list: list[int]):
        """能力ランクから 'A+1 S+1' 形式の文字列を返す"""
        s = ''
        for i,v in enumerate(rank_list):
            if rank_list[i]:
                s += f" {Pokemon.status_label[i]}{'+'*(v > 0)}{v}"
        return s[1:]

    def calculate_status(name: str, nature: str, efforts: list[int], indivs: list[int]=[31]*6) -> list[int]:
        p = Pokemon(name)
        p.nature = nature
        p.indiv = indivs
        p.effort = efforts
        p.update_status()
        return p.status

    def init(season=None):
        """ライブラリを初期化する"""

        # シーズンが指定されていなければ、最新のシーズンを取得する
        if season is None:
            dt_now = datetime.now(timezone(timedelta(hours=+9), 'JST'))
            y, m, d = dt_now.year, dt_now.month, dt_now.day
            season = max(12*(y-2022) + m - 11 - (d==1), 1)

        # タイプ画像コードの読み込み
        with open('data/terastal/codelist.txt', encoding='utf-8') as fin:
            for line in fin:
                data = line.split()
                Pokemon.type_file_code[data[1]] = data[0]
            #print(Pokemon.type_file_code)

        # テンプレート画像コードの読み込み
        with open('data/template/codelist.txt', encoding='utf-8') as fin:
            for line in fin:
                data = line.split()
                Pokemon.template_file_code[data[0]] = data[1]
            #print(Pokemon.template_file_code)

        # 図鑑の読み込み
        with open('data/zukan.txt', encoding='utf-8') as fin:
            next(fin)
            for line in fin:
                data = line.split()
                name = to_hankaku(data[1])
                Pokemon.zukan[name] = {}
                Pokemon.zukan[name]['type'] = [s for s in data[2:4] if s != '-' ]
                Pokemon.zukan[name]['ability'] = [s for s in data[4:8] if s != '-' ]
                Pokemon.zukan[name]['base'] = list(map(int, data[8:14]))

                for s in Pokemon.zukan[name]['ability']:
                    Pokemon.abilities.append(s)

                # 表示名の設定
                display_name = name
                if 'ロトム' in name:
                    display_name = 'ロトム'
                else:
                    if '(' in name:
                        display_name = name[:display_name.find('(')]
                    display_name = display_name.replace('パルデア','')
                    display_name = display_name.replace('ヒスイ','')
                    display_name = display_name.replace('ガラル','')
                    display_name = display_name.replace('アローラ','')
                    display_name = display_name.replace('ホワイト','')
                    display_name = display_name.replace('ブラック','')
                Pokemon.zukan[name]['display_name'] = display_name
                
                if display_name not in Pokemon.zukan_name:
                    Pokemon.zukan_name[display_name] = [name]
                elif name not in Pokemon.zukan_name[display_name]:
                    Pokemon.zukan_name[display_name].append(name)
                    # フォルム違いの差分を記録
                    for key in ['type', 'ability']:
                        if Pokemon.zukan[Pokemon.zukan_name[display_name][0]][key] != Pokemon.zukan[name][key]:
                            Pokemon.form_diff[display_name] = key
                            break

            Pokemon.abilities = list(set(Pokemon.abilities))
            Pokemon.abilities.sort()
            
            #print(Pokemon.zukan)
            #print(Pokemon.abilities)
            #print(Pokemon.zukan_name)
            #print(Pokemon.form_diff)

        # 外国語名の読み込み
        with open('data/foreign_name.txt', encoding='utf-8') as fin:
            next(fin)
            for line in fin:
                data = list(map(to_hankaku, line.split()))
                for i in range(len(data)):
                    Pokemon.japanese_display_name[to_hankaku(data[i])] = to_hankaku(data[0])
                Pokemon.foreign_display_names[to_hankaku(data[0])] = [to_hankaku(s) for s in data]
            #print(Pokemon.japanese_display_name)
            #print(Pokemon.foreign_display_names)

        # 体重の読み込み
        with open('data/weight.txt', encoding='utf-8') as fin:
            next(fin)
            for line in fin:
                data = line.split()
                Pokemon.zukan[to_hankaku(data[0])]['weight'] = float(data[1])

        # 特性の読み込み
        with open('data/ability_category.txt', encoding='utf-8') as fin:
            for line in fin:
                data = list(map(to_hankaku, line.split()))
                Pokemon.ability_category[data[0]] = data[1:]
                if 'ばけのかわ' in Pokemon.ability_category[data[0]]:
                    Pokemon.ability_category[data[0]].append('ばけのかわ+')
                #print(data[0]), print(Pokemon.ability_category[data[0]])

        # アイテムの読み込み
        with open('data/item.txt', encoding='utf-8') as fin:
            next(fin)
            for line in fin:
                data = line.split()
                item = to_hankaku(data[0])
                Pokemon.items[item] = {'power': int(data[1])} # なげつける威力
                if data[2] != '-':
                    Pokemon.item_buff_type[item] = data[2]
                if data[3] != '-':
                    Pokemon.item_debuff_type[item] = data[3]
                Pokemon.item_correction[item] = float(data[4])
                if int(data[5]):
                    Pokemon.consumable_items.append(item)

            Pokemon.item_correction[''] = 1
            #print(Pokemon.items)
            #print(Pokemon.item_correction)

        # 技の分類の読み込み
        with open('data/move_category.txt', encoding='utf-8') as fin:
            for line in fin:
                data = list(map(to_hankaku, line.split()))
                Pokemon.move_category[data[0]] = data[1:]
                #print(data[0]), print(Pokemon.move_category[data[0]])

        with open('data/move_value.txt', encoding='utf-8') as fin:
            for line in fin:
                data = line.split()
                Pokemon.move_value[data[0]] = {}
                for i in range(int(len(data[1:])/2)):
                    Pokemon.move_value[data[0]][to_hankaku(data[2*i+1])] = float(data[2*i+2])
                #print(data[0], Pokemon.move_value[data[0]])

        # 技の読み込み
        with open('data/move.txt', encoding='utf-8') as fin:
            eng = {'物理':'phy', '特殊':'spe'}
            next(fin)
            for line in fin:
                data = line.split()
                move = to_hankaku(data[0])
                if '変化' in data[2]:
                    data[2] = 'sta' + format(int(data[2][2:]), '04b')
                else:
                    data[2] = eng[data[2]]
                Pokemon.all_moves[move] = {
                    'type': data[1], # タイプ
                    'class': data[2], # 分類
                    'power': int(data[3]), # 威力
                    'hit': int(data[4]), # 命中率
                    'pp': int(int(data[5])*1.6) # PP
                }

            # 威力変動技を初期化する
            for move in Pokemon.move_category['power_var']:
                Pokemon.all_moves[move]['power'] = 1
 
       # 技の優先度の読み込み
        with open('data/move_priority.txt', encoding='utf-8') as fin:
            for line in fin:
                data = line.split()
                for move in data[1:]:
                    Pokemon.move_priority[to_hankaku(move)] = int(data[0])
            #print(Pokemon.move_priority)

       # 技の追加効果の読み込み
        with open('data/move_effect.txt', encoding='utf-8') as fin:
            next(fin)
            for line in fin:
                data = line.split()
                move = to_hankaku(data[0])
                Pokemon.move_effect[move] = {}
                Pokemon.move_effect[move]['object'] = int(data[1])
                Pokemon.move_effect[move]['prob'] = float(data[2])
                Pokemon.move_effect[move]['rank'] = [0] + list(map(int, data[3:10]))
                Pokemon.move_effect[move]['ailment'] = list(map(int, data[10:15]))
                Pokemon.move_effect[move]['confusion'] = int(data[15])
                Pokemon.move_effect[move]['flinch'] = float(data[16])
            #print(Pokemon.move_effect)

        # 連続技の読み込み
        with open('data/combo_move.txt', encoding='utf-8') as fin:
            for line in fin:
                data = line.split()
                Pokemon.combo_hit[to_hankaku(data[0])] = [int(data[1]), int(data[2])]
            #print(Pokemon.combo_hit)

        # 性格補正の読み込み
        with open('data/nature.txt', encoding='utf-8') as fin:
            for line in fin:
                data = line.split()
                Pokemon.nature_corrections[data[0]] = list(map(float, data[1:7]))
            #print(Pokemon.nature_corrections)

        # タイプ相性補正の読み込み
        with open('data/type.txt', encoding='utf-8') as fin:
            line = fin.readline()
            data = line.split()
            for i in range(len(data)):
                Pokemon.type_id[data[i]] = i
            for line in fin:
                data = line.split()
                Pokemon.type_corrections.append(list(map(float, data)))
            #print(Pokemon.type_id)
            #print(Pokemon.type_corrections)
       
        # ランクマッチの統計データの読み込み
        filename = 'battle_data/season'+str(season)+'.json'
        print(f'{filename}')
        with open(filename, encoding='utf-8') as fin:
            dict = json.load(fin)
            for org_name in dict:
                name = to_hankaku(org_name)
                Pokemon.home[name] = {}
                Pokemon.home[name]['nature'] = dict[org_name]['nature']
                Pokemon.home[name]['ability'] = dict[org_name]['ability']
                Pokemon.home[name]['item'] = dict[org_name]['item']
                Pokemon.home[name]['Ttype'] = dict[org_name]['Ttype']
                Pokemon.home[name]['move'] = dict[org_name]['move']

                # 半角表記に統一する
                for key in ['ability','item','move']:
                    for i,s in enumerate(Pokemon.home[name][key][0]):
                        Pokemon.home[name][key][0][i] = to_hankaku(s)

                # データの補完
                if not Pokemon.home[name]['nature'][0]:
                    Pokemon.home[name]['nature'] = [['まじめ'], [100]]
                if not Pokemon.home[name]['ability'][0]:
                    Pokemon.home[name]['ability'] = [[Pokemon.zukan[name]['ability'][0]], [100]]
                if not Pokemon.home[name]['item'][0]:
                    Pokemon.home[name]['item'] = [[''], [100]]
                if not Pokemon.home[name]['Ttype'][0]:
                    Pokemon.home[name]['Ttype'] = [[Pokemon.zukan[name]['type'][0]], [100]]
            
            #print(Pokemon.home.keys())

# ダメージ
class Damage:
    """ダメージを記録するためのクラス

    インスタンス変数
    ----------------------------------------
    self.turn: int
        ダメージが発生したターン。
    
    self.attack_player: int
        攻撃側のplayer。

    self.pokemon: list[Pokemon]
        場のPokemonインスタンス。

    self.move: str
        攻撃技。

    self.damage: int
        ダメージ。
    
    self.damage_ratio: float
        ダメージ割合。
    
    self.critical: bool
        急所ならTrue。
    
    self.stellar: [list[str], list[str]]
        ステラテラスタルで強化できるタイプ一覧。
    
    self.condition: dict
        ダメージ発生時の盤面条件 Battle.dict。
    """
    def __init__(self):
        self.turn = 0
        self.attack_player = 0
        self.index = [None, None]
        self.pokemon = [None, None]
        self.move = None
        self.damage = None
        self.damage_ratio = None
        self.critical = False
        self.stellar = [[], []]
        self.condition = {}

class Battle:
    """二人のplayerによるポケモン対戦を表現するクラス。
    主な機能は、ダメージ計算、リーサル計算、対戦シミュレーション。

    インスタンス変数
    ----------------------------------------
    self.pokemon: [Pokemon, Pokemon]
        場のポケモン。
    
    self.selected: [list[Pokemon], list[Pokemon]]
        選出されたポケモン。

    self.observed = [list[Pokemon], list[Pokemon]]
        観測されたポケモン。
        
        self.observed[player].speed_range: list[int]
            過去のターンの行動順から判別した、とりうる素早さの範囲。[min, max]

    self.condition: dict
        盤面状況。

    ----------------------------------------
    ダメージ計算用の変数 (抜粋)
    ----------------------------------------
    self.damage_log: [list[str], list[str]]
        ダメージ計算時の補正項や消費されたアイテムを記録する。

    ----------------------------------------
    リーサル計算用の変数 (抜粋)
    ----------------------------------------
    self.damage_dict: dict
        {ダメージ: 場合の数}

    self.hp_dict: dict
        {残りHP: 場合の数}

    self.lethal_num: int
        確定数。
    
    self.lethal_prob: float
        致死率。

    ----------------------------------------
    対戦シミュレーション用の変数 (抜粋)
    ----------------------------------------
    self.log: [list[str], list[str]]
        ターン処理のログ。

    self.turn: int
        ターン。
        
    self.command: [int, int]
        ターン開始時に指定したコマンド。

    self.change_command_history: [list[int], list[int]]
        交代コマンドの履歴

    self.move: [str, str]
        選択された技。

    self.was_valid: [bool, bool]
        技が成功したらTrue。
        
    self.action_order: [int, int]
        [先手のplayer, 後手のplayer]

    self.stellar: [list[str], list[str]]
        ステラで強化できる残りタイプのリスト。

    self.standby : [bool, bool]
        playerがまだ行動していなければTrue。
    """

    # コマンド
    SKIP = -1
    STRUGGLE = 30
    NO_COMMAND = 40

    def __init__(self, seed: int=None):
        self.seed = seed if seed is not None else int(time.time())
        self.copy_count = 0
        self.reset_game()

        # ダメージ計算
        self.damage_log = [[], []]
        self.critical = False

        # リーサル計算
        self.damage_dict = {}
        self.hp_dict = {}
        self.lethal_num = 0
        self.lethal_prob = 0

        # 対戦シミュレーション
        self.command = [None, None]
        self.change_command_history = [[], []]
        self.was_valid = [True, True]

    def reset_game(self):
        """試合開始前の状態に初期化する"""
        self.pokemon = [None, None]
        self.selected = [[], []]
        self.observed = [[], []]
        self.damage_history = []
        self.stellar = [list(Pokemon.type_id.keys())]*2

        self.condition = {
            'sunny': 0,             # はれ 残りターン
            'rainy': 0,             # あめ 残りターン
            'snow': 0,              # ゆき 残りターン
            'sandstorm': 0,         # すなあらし 残りターン
            'elecfield': 0,         # エレキフィールド 残りターン
            'glassfield': 0,        # グラスフィールド 残りターン
            'psycofield': 0,        # サイコフィールド 残りターン
            'mistfield': 0,         # ミストフィールド 残りターン
            'gravity': 0,           # じゅうりょく 残りターン
            'trickroom': 0,         # トリックルーム 残りターン

            'reflector': [0, 0],    # リフレクター 残りターン
            'lightwall': [0, 0],    # ひかりのかべ 残りターン
            'oikaze': [0, 0],       # おいかぜ 残りターン
            'safeguard': [0, 0],    # しんぴのまもり 残りターン
            'whitemist': [0, 0],    # しろいきり 残りターン
            'makibishi': [0, 0],    # まきびし カウント
            'dokubishi': [0, 0],    # どくびし カウント
            'stealthrock': [0, 0],  # ステルスロック
            'nebanet': [0, 0],      # ねばねばネット
            'wish': [0, 0],         # ねがいごと (残りターン)+0.001*(回復量)
        }

        # 対戦シミュレーション
        self._random = random.Random(self.seed)
        self.turn = -1
        self.reserved_change_commands = [[], []]
        self._dump = {}

        # breakpoint
        # 対戦シミュレーションにおいて、交代コマンド入力時に処理を中断したところから
        # self.proceed()によってターンを再開(再現)する際、再開地点を追跡するために用いるフラグ。
        self.breakpoint = ['', '']

        self.reset_sim_parameters()

    def current_index(self, player: int) -> int:
        """場のポケモンの選出番号を返す"""
        return self.selected[player].index(self.pokemon[player])
    
    def eff_speed(self, player: int) -> int:
        """特性やアイテムを考慮した、{player}の場のポケモンの実質的な素早さを返す"""
        p = self.pokemon[player]
        speed = int(p.status[5]*p.rank_correction(5))

        if p.boost_index == 5:
            speed = int(speed*1.5)
        
        r = 4096

        match p.ability:
            case 'かるわざ+':
                r = round_half_up(r*2)
            case 'サーフテール':
                if self.condition['elecfield']:
                    r = round_half_up(r*2)
            case 'すいすい':
                if self.weather(player) == 'rainy':
                    r = round_half_up(r*2)
            case 'すなかき':
                if self.weather() == 'sandstorm':
                    r = round_half_up(r*2)
            case 'スロースタート' | 'スロースタート+' | 'スロースタート++' | 'スロースタート+++' | 'スロースタート++++':
                r = round_half_up(r*0.5)
            case 'はやあし':
                if p.ailment:
                    r = round_half_up(r*1.5)
            case 'ゆきかき':
                if self.weather() == 'snow':
                    r = round_half_up(r*2)
            case 'ようりょくそ':
                if self.weather(player) == 'sunny':
                    r = round_half_up(r*2)
        
        match p.item:
            case 'くろいてっきゅう':
                r = round_half_up(r*0.5)
            case 'こだわりスカーフ':
                r = round_half_up(r*1.5)
        
        if self.condition['oikaze'][player]:
            r = round_half_up(r*2)
        
        speed = round_half_down(speed*r/4096)

        if p.ailment == 'PAR' and p.ability != 'はやあし':
            speed = int(speed*0.5)
        
        return speed

    def ability(self, player: int, move: str='') -> str:
        """ダメージ発生時における{player}の場のポケモンの特性を返す。
            かたやぶりや{move}によって無効化される場合は''を返す。
        """
        p1 = self.pokemon[player] # 手番
        p2 = self.pokemon[not player] # 相手側
        
        if not move or p1.item == 'とくせいガード' or p1.ability in Pokemon.ability_category['undeniable']:
            return p1.ability

        if move in ['シャドーレイ','フォトンゲイザー','メテオドライブ'] or \
            p2.ability in ['かたやぶり','ターボブレイズ','テラボルテージ'] or \
            (p2.ability == 'きんしのちから' and 'sta' in Pokemon.all_moves[move]['class']):
            return ''

        return p1.ability

    def is_float(self, player: int) -> bool:
        """{player}の場のポケモンがふゆう状態ならTrueを返す"""
        p = self.pokemon[player]
        if p.item == 'くろいてっきゅう' or p.condition['anti_air'] or p.condition['neoharu'] or self.condition['gravity']:
            return False
        else:
            return 'ひこう' in p.types or p.ability == 'ふゆう' or p.item == 'ふうせん' or p.condition['magnetrise']

    def is_overcoat(self, player: int, move: str='') -> bool:
        """{player}の場のポケモンがぼうじん状態ならTrueを返す"""
        return self.pokemon[player].item == 'ぼうじんゴーグル' or self.ability(player, move) == 'ぼうじん'

    def is_nervous(self, player: int) -> bool:
        """{player}の場のポケモンがきんちょうかん状態ならTrueを返す"""
        return self.pokemon[not player].ability in ['きんちょうかん','じんばいったい']

    def move_type(self, player: int, move: str) -> str:
        """{player}の場のポケモンが{move}を使用したときの技のタイプを返す"""
        p = self.pokemon[player]
        move_type = Pokemon.all_moves[move]['type']
        
        if move in ['テラバースト','テラクラスター'] and p.terastal:
            return p.Ttype
        
        match p.ability:
            case 'うるおいボイス':
                if move in Pokemon.move_category['sound']:
                    return 'みず'
            case 'エレキスキン':
                if move_type == 'ノーマル':
                    return 'でんき'
            case 'スカイスキン':
                if move_type == 'ノーマル':
                    return 'ひこう'
            case 'ノーマルスキン':
                return 'ノーマル'
            case 'フェアリースキン':
                if move_type == 'ノーマル':
                    return 'フェアリー'
            case 'フリーズスキン':
                if move_type == 'ノーマル':
                    return 'こおり'

        match move:
            case 'ウェザーボール':
                t = {'':'ノーマル', 'sunny':'ほのお', 'rainy':'みず', 'snow':'こおり', 'sandstorm':'いわ'}
                return t[self.weather(player)]
            case 'さばきのつぶて' | 'めざめるダンス':
                return p.types[0]
            case 'ツタこんぼう':
                if 'オーガポン(' in p.name:
                    return p.org_types[-1]
            case 'レイジングブル':
                return p.types[-1]
        
        return move_type

    def weather(self, player: int=None) -> str:
        """現在の天候を返す。{player}を指定すると、ばんのうがさを考慮する"""
        if any(s in [p.ability for p in self.pokemon] for s in ['エアロック', 'ノーてんき']):
            return ''
        for s in Pokemon.weathers:
            if self.condition[s]:
                if player in range(2) and self.pokemon[player].item == 'ばんのうがさ' and s in ['sunny','rainy']:
                    return ''
                else:
                    return s
        return ''

    def field(self) -> str:
        """現在のフィールドを返す"""
        for s in Pokemon.fields:
            if self.condition[s]:
                return s
        return ''

    def can_terastal(self, player: int) -> bool:
        """{player}がテラスタルを使用可能ならTrueを返す"""
        if not self.selected[player]:
            return True
        else:
            return not any(p.terastal for p in self.selected[player])

    # ダメージ計算
    def attack_type_correction(self, player: int, move: str) -> float:
        """{player}の場のポケモンが{move}を使用したときの攻撃タイプ補正値を返す"""
        r = 1
        p1 = self.pokemon[player] # 攻撃側
        move_type = self.move_type(player, move)

        if p1.terastal and move not in ['テラバースト']:
            r0 = r
            if p1.Ttype == 'ステラ' and move_type in self.stellar[player]:
                if move_type in p1.org_types:
                    r = r*2.25 if p1.ability == 'てきおうりょく' else r*2.0
                else:
                    r *= 1.2
                self.damage_log[player].append(f'{p1.Ttype}テラスタル x{r/r0:.1f}')
            elif move_type == p1.Ttype:
                if p1.Ttype in p1.org_types:
                    r = r*2.25 if p1.ability == 'てきおうりょく' else r*2.0
                else:
                    r = r*2 if p1.ability == 'てきおうりょく' else r*1.5
                self.damage_log[player].append(f'{p1.Ttype}テラスタル x{r/r0:.1f}')
            elif move_type in p1.org_types:
                r *= 1.5
        else:
            if move_type in p1.types:
                r = r*2 if p1.ability == 'てきおうりょく' else r*1.5
        return r
    
    def defence_type_correction(self, player: int, move: str, self_harm: bool=False) -> float:
        """{player}の場のポケモンが{move}を使用したときの防御タイプ補正値を返す。
        {self_harm}=Trueなら自傷とみなす。
        """
        player2 = player if self_harm else not player
        p1 = self.pokemon[player] # 攻撃側
        p2 = self.pokemon[player2] # 防御側
        ability2 = self.ability(player2, move)
        move_type = self.move_type(player, move)

        r = 1        

        if move_type == 'ステラ' and p2.terastal:
            r = 2
        else:
            for t in p2.types:
                if p1.ability in ['しんがん','きもったま'] and t=='ゴースト' and move_type in ['ノーマル','かくとう']:
                    self.damage_log[player].append(p1.ability)
                elif move == 'フリーズドライ' and t == 'みず':
                    r *= 2
                elif not self.is_float(player2) and move_type == 'じめん' and t == 'ひこう':
                    continue
                else:
                    r *= Pokemon.type_corrections[Pokemon.type_id[move_type]][Pokemon.type_id[t]]
                    if move == 'フライングプレス':
                        r *= Pokemon.type_corrections[Pokemon.type_id['ひこう']][Pokemon.type_id[t]]
                    if r == 0:
                        if p2.item == 'ねらいのまと':
                            r = 1
                        else:
                            break

        if ability2 == 'テラスシェル' and r and p2.hp == p2.status[0]:
            r = 0.5
            self.damage_log[player].append(f'{ability2} x{r:.1f}')

        return r
    
    def power_correction(self, player: int, move: str, self_harm: bool=False) -> float:
        """{player}の場のポケモンが{move}を使用したときの威力補正値を返す。
        {self_harm}=Trueなら自傷とみなす。
        """
        player2 = player if self_harm else not player
        p1 = self.pokemon[player] # 攻撃側
        p2 = self.pokemon[player2] # 防御側
        move_type = self.move_type(player, move)
        move_class = p1.move_class(move)
        move_power = Pokemon.all_moves[move]['power']

        r = 4096

        # 攻撃側
        if 'オーガポン(' in p1.name:
            r = round_half_up(r*4915/4096)
            self.damage_log[player].append('おめん x1.2')

        # 威力変動技
        r0 = r
        match move:
            case 'アクロバット':
                if not p1.item:
                    r = round_half_up(r*2)
            case 'アシストパワー' | 'つけあがる':
                r = round_half_up(r*(1 + sum(v for v in p1.rank[1:] if v >= 0)))
            case 'ウェザーボール':
                if self.weather(player):
                    r = round_half_up(r*2)
            case 'エレキボール':
                x = self.eff_speed(player)/self.eff_speed(player2)
                if x >= 4:
                    r *= 150
                elif x >= 3:
                    r *= 120
                elif x >= 2:
                    r *= 80
                elif x >= 1:
                    r *= 60
                else:
                    r *= 40
            case 'おはかまいり':
                r *= (1 + sum(1 for p in self.selected[player] if p.hp == 0))
            case 'からげんき':
                if p1.ailment:
                    r = round_half_up(r*2)
            case 'きしかいせい' | 'じたばた':
                x = int(48*p1.hp/p1.status[0])
                if x <= 1:
                    r *= 200
                elif x <= 4:
                    r *= 150
                elif x <= 9:
                    r *= 100
                elif x <= 16:
                    r *= 80
                elif x <= 32:
                    r *= 40
                else:
                    r *= 20
            case 'くさむすび' | 'けたぐり':
                weight = p2.weight
                if weight < 10:
                    r *= 20
                elif weight < 25:
                    r *= 40
                elif weight < 50:
                    r *= 60
                elif weight < 100:
                    r *= 80
                elif weight < 200:
                    r *= 100
                else:
                    r *= 120
            case 'しおふき' | 'ドラゴンエナジー' | 'ふんか':
                r = int(r*p1.hp/p1.status[0])
            case 'しおみず':
                if p2.hp <= p2.status[0]/2:
                    r = round_half_up(r*2)
            case 'じだんだ' | 'やけっぱち':
                pass
            case 'しっぺがえし':
                if player == self.action_order[-1]:
                    r = round_half_up(r*2)
            case 'ジャイロボール':
                r = round_half_up(r*min(150, int(1+25*self.eff_speed(player2)/self.eff_speed(player))))
            case 'Gのちから':
                if self.condition['gravity']:
                    r = round_half_up(r*1.5)
            case 'たたりめ' | 'ひゃっきやこう':
                if p2.ailment:
                    r = round_half_up(r*2)
            case 'テラバースト':
                if p1.Ttype == 'ステラ' and p1.terastal:
                    r = round_half_up(r*1.25)
            case 'なげつける':
                r = r*Pokemon.items[p1.item]['power'] if p1.item else 0
            case 'にぎりつぶす' | 'ハードプレス':
                p0 = 120 if move == 'にぎりつぶす' else 100
                r *= round_half_down(p0*p2.hp/p2.status[0])
            case 'はたきおとす':
                if p2.item:
                    r = round_half_up(r*1.5)
            case 'ふんどのこぶし':
                r *= (1 + p1.n_attacked)
            case 'ベノムショック':
                if p2.ailment == 'PSN':
                    r = round_half_up(r*2)
            case 'ヒートスタンプ' | 'ヘビーボンバー':
                weight1, weight2 = p1.weight, p2.weight
                if 2*weight2 > weight1:
                    r *= 40
                elif 3*weight2 > weight1:
                    r *= 60
                elif 4*weight2 > weight1:
                    r *= 80
                elif 5*weight2 > weight1:
                    r *= 100
                else:
                    r *= 120
            case 'ゆきなだれ' | 'リベンジ':
                if player == self.action_order[-1] and self.damage[player2]:
                    r = round_half_up(r*2)
        if r0 != r:
            self.damage_log[player].append(f'{move} x{r/r0:.1f}')

        if p1.ability == 'テクニシャン' and move_power*r/4096 <= 60:
            r = round_half_up(r*1.5)
            self.damage_log[player].append(f'{p1.ability} x1.5')

        # 以降の技はテクニシャン非適用
        if move in ['ソーラービーム','ソーラーブレード']:
            rate = 0.5 if self.weather() == 'sandstorm' else 1
            r = round_half_up(r*rate)
            if rate != 1:
                self.damage_log[player].append(f'{move} x{rate}')
        
        r0 = r
        match p1.ability:
            case 'アナライズ':
                if player == self.action_order[-1]:
                    r = round_half_up(r*5325/4096)
            case 'エレキスキン':
                if Pokemon.all_moves[move]['type'] == 'ノーマル':
                    r = round_half_up(r*4915/4096)
            case 'かたいつめ':
                if move in Pokemon.move_category['contact']:
                    r = round_half_up(r*5325/4096)
            case 'がんじょうあご':
                if move in Pokemon.move_category['bite']:
                    r = round_half_up(r*1.5)
            case 'きれあじ':
                if move in Pokemon.move_category['cut']:
                    r = round_half_up(r*1.5)
            case 'スカイスキン':
                if Pokemon.all_moves[move]['type'] == 'ノーマル':
                    r = round_half_up(r*4915/4096)
            case 'すてみ':
                if move in Pokemon.move_value['rebound'] or move in Pokemon.move_value['mis_rebound']:
                    r = round_half_up(r*4915/4096)
            case 'すなのちから':
                if self.weather() == 'sandstorm' and move_type in ['いわ','じめん','はがね']:
                    r = round_half_up(r*5325/4096)
            case 'そうだいしょう':
                ls = [4096, 4506, 4915, 5325, 5734, 6144]
                n = sum(p.hp == 0 for p in self.selected[player])
                r = round_half_up(r*ls[n]/4096)
            case 'ダークオーラ' | 'フェアリーオーラ':
                if (p1.ability == 'ダークオーラ' and move_type == 'あく') or (p1.ability == 'フェアリーオーラ' and move_type == 'フェアリー'):
                    v = 5448/4096
                    if p2.ability == 'オーラブレイク':
                        v = 1/v
                    r = round_half_up(r*v)
            case 'ちからずく':
                if move in Pokemon.move_category['effect']:
                    r = round_half_up(r*5325/4096)
            case 'てつのこぶし':
                if move in Pokemon.move_category['punch']:
                    r = round_half_up(r*4915/4096)
            case 'とうそうしん':
                match p1.sex*p2.sex:
                    case 1:
                        r = round_half_up(r*1.25)
                    case -1:
                        r = round_half_up(r*3072/4096)
            case 'どくぼうそう':
                if p1.ailment == 'PSN' and move_class == 'phy':
                    r = round_half_up(r*1.5)
            case 'ノーマルスキン':
                if move != 'わるあがき' and Pokemon.all_moves[move]['type'] != 'ノーマル':
                    r = round_half_up(r*4915/4096)
            case 'パンクロック':
                if move in Pokemon.move_category['sound']:
                    r = round_half_up(r*5325/4096)
            case 'フェアリースキン':
                if Pokemon.all_moves[move]['type'] == 'ノーマル':
                    r = round_half_up(r*4915/4096)
            case 'フリーズスキン':
                if Pokemon.all_moves[move]['type'] == 'ノーマル':
                    r = round_half_up(r*4915/4096)
            case 'メガランチャー':
                if move in Pokemon.move_category['wave']:
                    r = round_half_up(r*1.5)
        if r != r0:
            self.damage_log[player].append(f'{p1.ability} x{r/r0:.1f}')

        r0 = r
        match p1.item:
            case 'しらたま' | 'だいしらたま':
                if 'パルキア' in p1.name and move_type in ['みず','ドラゴン']:
                    r = round_half_up(r*4915/4096)
            case 'こころのしずく':
                if p1.name in ['ラティオス','ラティアス'] and move_type in ['エスパー','ドラゴン']:
                    r = round_half_up(r*4915/4096)
            case 'こんごうだま' | 'だいこんごうだま':
                if 'ディアルガ' in p1.name and move_type in ['はがね','ドラゴン']:
                    r = round_half_up(r*4915/4096)
            case 'はっきんだま' | 'だいはっきんだま':
                if 'ギラティナ' in p1.name and move_type in ['ゴースト','ドラゴン']:
                    r = round_half_up(r*4915/4096)
            case 'ちからのハチマキ':
                if move_class == 'phy':
                    r = round_half_up(r*4505/4096)
            case 'ノーマルジュエル':
                if move_type == 'ノーマル':
                    r = round_half_up(r*5325/4096)
                    self.damage_log[player].append(p1.item) # アイテム消費判定用
            case 'パンチグローブ':
                if move in Pokemon.move_category['punch']:
                    r = round_half_up(r*4506/4096)
            case 'ものしりメガネ':
                if move_class == 'spe':
                    r = round_half_up(r*4505/4096)
            case p1.item if p1.item in Pokemon.item_buff_type:
                if move_type == Pokemon.item_buff_type[p1.item]:
                    r = round_half_up(r*4915/4096)
        if r != r0:
            self.damage_log[player].append(f'{p1.item} x{r/r0:.1f}')

        # フィールド補正
        r0 = r
        if self.condition['elecfield']:
            if move_type=='でんき' and not self.is_float(player):
                r = round_half_up(r*5325/4096)
            if move == 'ライジングボルト' and not self.is_float(not player):
                r = round_half_up(r*2)
        elif self.condition['glassfield']:
            if move_type == 'くさ' and not self.is_float(player):
                r = round_half_up(r*5325/4096)
            if move in ['じしん','じならし','マグニチュード'] and not self.is_float(not player):
                r = round_half_up(r*0.5)
        elif self.condition['psycofield']:
            if move_type == 'エスパー' and not self.is_float(player):
                r = round_half_up(r*5325/4096)
            if move == 'ワイドフォース' and not self.is_float(not player):
                r = round_half_up(r*1.5)
        elif self.condition['mistfield']:
            if move_type == 'ドラゴン' and not self.is_float(not player):
                r = round_half_up(r*0.5)
            if move == 'ミストバースト' and not self.is_float(player):
                r = round_half_up(r*1.5)
        if r != r0:
            self.damage_log[player].append(f'フィールド x{r/r0:.1f}')

        # 防御側の特性
        r0 = r
        match self.ability(player2, move):
            case 'かんそうはだ':
                if move_type == 'ほのお':
                    r = round_half_up(r*1.25)
                elif move_type == 'みず':
                    r = 0
                    self.damage_log[player].append(p2.ability) # 特性発動判定用
            case 'たいねつ':
                if move_type == 'ほのお':
                    r = round_half_up(r*0.5)
        if r != r0:
            self.damage_log[player].append(f'{p2.ability} x{r/r0:.1f}')

        return r
    
    def attack_correction(self, player: int, move: str, self_harm: bool=False) -> float:
        """{player}の場のポケモンが{move}を使用したときの攻撃補正値を返す。
        {self_harm}=Trueなら自傷とみなす。
        """
        player2 = player if self_harm else not player
        p1 = self.pokemon[player] # 攻撃側
        p2 = self.pokemon[player2] # 防御側
        move_type = self.move_type(player, move)
        move_class = p1.move_class(move)

        r = 4096

        # 攻撃側
        if (move_class == 'phy' and p1.boost_index == 1) or (move_class == 'spe' and p1.boost_index == 3):
            r = round_half_up(r*5325/4096)
            self.damage_log[player].append('ブーストエナジーAC x1.3')

        r0 = r
        match p1.ability:
            case 'いわはこび':
                if move_type == 'いわ':
                    r = round_half_up(r*1.5)
            case 'げきりゅう':
                if move_type == 'みず' and p1.hp/p1.status[0] <= 1/3:
                    r = round_half_up(r*1.5)
            case 'ごりむちゅう':
                if move_class == 'phy':
                    r = round_half_up(r*1.5)
            case 'こんじょう':
                if p1.ailment and move_class == 'phy':
                    r = round_half_up(r*1.5)
            case 'サンパワー':
                if self.weather() == 'sunny' and move_class == 'spe':
                    r = round_half_up(r*1.5)
            case 'しんりょく':
                if move_type == 'くさ' and p1.hp/p1.status[0] <= 1/3:
                    r = round_half_up(r*1.5)
            case 'すいほう':
                if move_type == 'みず':
                    r = r = round_half_up(r*2)
            case 'スロースタート' | 'スロースタート+' | 'スロースタート++' | 'スロースタート+++' | 'スロースタート++++':
                    r = round_half_up(r*0.5)
            case 'ちからもち' | 'ヨガパワー':
                if move_class == 'phy':
                    r = round_half_up(r*2)
            case 'トランジスタ':
                if move_type=='でんき':
                    r = round_half_up(r*1.3)
            case 'ねつぼうそう':
                if p1.ailment == 'BRN' and move_class == 'spe':
                    r = round_half_up(r*1.5)
            case 'はがねつかい' | 'はがねのせいしん':
                if move_type=='はがね':
                    r = round_half_up(r*1.5)
            case 'ハドロンエンジン':
                if self.condition['elecfield']:
                    r = round_half_up(r*5461/4096)
            case 'はりこみ':
                if self.has_changed[player2]:
                    r = round_half_up(r*2)
            case 'ひひいろのこどう':
                if self.weather() == 'sunny':
                    r = round_half_up(r*5461/4096)
            case 'フラワーギフト':
                if self.weather() == 'sunny':
                    r = round_half_up(r*1.5)
            case 'むしのしらせ':
                if move_type == 'むし' and p1.hp/p1.status[0] <= 1/3:
                    r = round_half_up(r*1.5)
            case 'もうか':
                if move_type == 'ほのお' and p1.hp/p1.status[0] <= 1/3:
                    r = round_half_up(r*1.5)
            case 'よわき':
                if p1.hp/p1.status[0] <= 1/2:
                    r = round_half_up(r*0.5)
            case 'りゅうのあぎと':
                if move_type == 'ドラゴン':
                    r = round_half_up(r*1.5)
        if r != r0:
            self.damage_log[player].append(f'{p1.ability} x{r/r0:.1f}')

        if 'もらいび+' in p1.ability and move_type == 'ほのお':
            r = round_half_up(r*1.5)
            p1.ability = 'もらいび'
            self.damage_log[player].append(f'もらいび x1.5')

        r0 = r
        match p1.item:
            case 'こだわりハチマキ':
                if move_class == 'phy':
                    r = round_half_up(r*1.5)
            case 'こだわりメガネ':
                if move_class == 'spe':
                    r = round_half_up(r*1.5)
            case 'でんきだま':
                if p1.name == 'ピカチュウ':
                    r = round_half_up(r*2)
        if r != r0:
            self.damage_log[player].append(f'{p1.item} x{r/r0:.1f}')

        # 防御側
        r0 = r
        match self.ability(player2, move):
            case 'あついしぼう':
                if move_type in ['ほのお', 'こおり']:
                    r = round_half_up(r*0.5)
            case 'きよめのしお':
                if move_type == 'ゴースト':
                    r = round_half_up(r*0.5)
            case 'わざわいのうつわ':
                if move_class == 'spe':
                    r = round_half_up(r*3072/4096)
            case 'わざわいのおふだ':
                if move_class == 'phy':
                    r = round_half_up(r*3072/4096)
        if r != r0:
            self.damage_log[player].append(f'{p2.ability} x{r/r0:.2f}')

        return r
    
    def defence_correction(self, player: int, move: str, self_harm: bool=False) -> float:
        """{player}の場のポケモンが{move}を使用したときの防御補正値を返す。
        {self_harm}=Trueなら自傷とみなす。
        """
        player2 = player if self_harm else not player
        p1 = self.pokemon[player] # 攻撃側
        p2 = self.pokemon[player2] # 防御側
        move_type = self.move_type(player, move)
        move_class = p1.move_class(move)

        r = 4096

        # 攻撃側
        r0 = r
        match p1.ability:
            case 'わざわいのたま':
                if move_class == 'spe' and move not in Pokemon.move_category['physical']:
                    r = round_half_up(r*3072/4096)
            case 'わざわいのつるぎ':
                if move_class == 'phy' or move in Pokemon.move_category['physical']:
                    r = round_half_up(r*3072/4096)
        if r != r0:
            self.damage_log[player].append(f'{p1.ability} x{r0/r:.2f}')

        # 防御側
        if ((move_class == 'phy' or move in Pokemon.move_category['physical']) and p2.boost_index == 2) or \
            (move_class == 'spe' and move not in Pokemon.move_category['physical'] and p2.boost_index == 4):
            r = round_half_up(r*5325/4096)
            self.damage_log[player].append('ブーストエナジーBD x0.77')

        r0 = r
        match p2.item:
            case 'しんかのきせき':
                if True:
                    r = round_half_up(r*1.5)
            case 'とつげきチョッキ':
                if move_class == 'spe' and move not in Pokemon.move_category['physical']:
                    r = round_half_up(r*1.5)
        if r != r0:
            self.damage_log[player].append(f'{p2.item} x{r0/r:.2f}')

        r0 = r
        match self.ability(player2, move):
            case 'くさのけがわ':
                if self.condition['glassfield'] and (move_class == 'phy' or move in Pokemon.move_category['physical']):
                    r = round_half_up(r*1.5)
            case 'すいほう':
                if move_type == 'ほのお':
                    r = round_half_up(r*2)
            case 'ファーコート':
                if move_class == 'phy' or move in Pokemon.move_category['physical']:
                    r = round_half_up(r*2)
            case 'ふしぎなうろこ':
                if p2.ailment and (move_class == 'phy' or move in Pokemon.move_category['physical']):
                    r = round_half_up(r*1.5)
            case 'フラワーギフト':
                if self.weather() == 'sunny':
                    r = round_half_up(r*1.5)
        if r != r0:
            self.damage_log[player].append(f'{p2.ability} x{r0/r:.2f}')

        return r
    
    def damage_correction(self, player, move, self_harm=False, lethal=False):
        """{player}の場のポケモンが{move}を使用したときのダメージ補正値を返す。
        {self_harm}=Trueなら自傷とみなす。
        """
        player2 = player if self_harm else not player
        p1 = self.pokemon[player] # 攻撃側
        p2 = self.pokemon[player2] # 防御側
        move_type = self.move_type(player, move)
        move_class = p1.move_class(move)        

        r = 4096
        r_defence_type = self.defence_type_correction(player, move)

        r0 = r
        match move:
            case 'アクセルブレイク' | 'イナズマドライブ':
                if r_defence_type > 1:
                    r = round_half_up(r*5461/4096)
            case 'じしん' | 'マグニチュード':
                if p2.hide_move == 'あなをほる':
                    r *= 2
            case 'なみのり':
                if p2.hide_move == 'ダイビング':
                    r *= 2
        if r != r0:
            self.damage_log[player].append(f'{move} x{r/r0:.2f}')

        # 攻撃側の特性
        match p1.ability:
            case 'いろめがね':
                if r_defence_type < 1:
                    r *= 2
                    self.damage_log[player].append(f'{p1.ability} x2')

            case 'スナイパー':
                if self.critical:
                    r = round_half_up(r*1.5)
                    self.damage_log[player].append('スナイパー x1.5')

        # 防御側の特性
        r0 = r
        match self.ability(player2, move):
            case 'かぜのり':
                if move in Pokemon.move_category['wind']:
                    r = 0
                    self.damage_log[player].append(p2.ability) # 特性発動判定用
            case 'こおりのりんぷん':
                if move_class == 'spe':
                    r = round_half_up(r*0.5)
            case 'こんがりボディ':
                if move_type == 'ほのお':
                    r = 0
                    self.damage_log[player].append(p2.ability) # 特性発動判定用
            case 'そうしょく':
                if move_type == 'くさ':
                    r = 0
                    self.damage_log[player].append(p2.ability) # 特性発動判定用
            case 'ちくでん' | 'でんきエンジン' | 'ひらいしん':
                if move_type == 'でんき':
                    r = 0
                    self.damage_log[player].append(p2.ability) # 特性発動判定用
            case 'ちょすい' | 'よびみず':
                if move_type == 'みず':
                    r = 0
                    self.damage_log[player].append(p2.ability) # 特性発動判定用
            case 'どしょく':
                if move_type == 'じめん':
                    r = 0
                    self.damage_log[player].append(p2.ability) # 特性発動判定用
            case 'ハードロック':
                if self.defence_type_correction(player, move) > 1:
                    r = round_half_up(r*0.75)
            case 'パンクロック':
                if move in Pokemon.move_category['sound']:
                    r = round_half_up(r*0.5)
            case 'フィルター' | 'プリズムアーマー':
                if self.defence_type_correction(player, move) > 1:
                    r = round_half_up(r*3072/4096)
            case 'ぼうおん':
                if move in Pokemon.move_category['sound']:
                    r = 0
            case 'ぼうだん':
                if move in Pokemon.move_category['bullet']:
                    r = 0
            case 'ファントムガード' | 'マルチスケイル':
                if not lethal and p2.hp == p2.status[0]:
                    r = round_half_up(r*0.5)
            case 'もふもふ':
                if move_type == 'ほのお':
                    r = round_half_up(r*2)
                elif move in Pokemon.move_category['contact']:
                    r = round_half_up(r*0.5)
        if r != r0:
            self.damage_log[player].append(f'{p2.ability} x{r/r0:.2f}')

        if 'もらいび' in self.ability(player2, move) and move_type == 'ほのお':
            r = 0
            self.damage_log[player].append('もらいび x0.0')
            self.damage_log[player].append('もらいび') # 特性発動判定用

        # 攻撃側のアイテム
        r0 = r
        match p1.item:
            case 'いのちのたま':
                r = round_half_up(r*5324/4096)
            case 'たつじんのおび':
                if r_defence_type > 1:
                    r = round_half_up(r*4915/4096)
        if r != r0:
            self.damage_log[player].append(f'{p1.item} x{r/r0:.1f}')

        # 壁
        if not self.critical and p1.ability != 'すりぬけ' and move not in Pokemon.move_category['wall_break']:
            if self.condition['reflector'][player2] and move_class == 'phy':
                r = round_half_up(r*0.5)
                self.damage_log[player].append('リフレクター x0.5')

            if self.condition['lightwall'][player2] and move_class == 'spe':
                r = round_half_up(r*0.5)
                self.damage_log[player].append('ひかりのかべ x0.5')

        # 粉技無効
        if move in Pokemon.move_category['powder']:
            if self.is_overcoat(player2, move):
                r = 0
                self.damage_log[player].append('ぼうじん')
            elif move != 'わたほうし' and 'くさ' in p2.types:
                r = 0
                self.damage_log[player].append('粉わざ x0.0')

        if move_type == 'じめん' and self.is_float(player2):
            r = 0
            self.damage_log[player].append('浮遊 x0.0')

        # 半減実
        r0 = r
        if p2.item in Pokemon.item_debuff_type and not self.is_nervous(player2):
            if Pokemon.item_debuff_type[p2.item] == 'ノーマル' and move_type == 'ノーマル':
                r = round_half_up(r*0.5)
            elif r_defence_type > 1 and move_type == Pokemon.item_debuff_type[p2.item]:
                r = round_half_up(r*0.5)
        if r != r0:
            self.damage_log[player].append(f'{p2.item} x{r/r0:.1f}')
            self.damage_log[player2].append(p2.item) # アイテム消費判定用

        return r
 
    def oneshot_damages(self, player: int, move: str, critical: bool=False, power_factor: float=1, \
                        self_harm: bool=False, lethal: bool=False) -> list[int]:
        """1ヒットあたりのダメージを返す
        Parameters
        ----------
        player: int
            攻撃側のplayer。
        
        move: str
            攻撃技。
        
        critical: bool
            Trueなら急所に当たったときのダメージを計算する。
        
        power_factor: float
            任意の威力補正量。トリプルアクセルの計算に使用する。
        
        self_harm: bool
            Trueなら攻撃対象を自分自身にする。
        
        lethal: bool
            リーサル計算時のみTrueを指定する。

        Returns
        ----------
        damage: list[int]
            乱数により分岐したダメージのリスト。
        """        
        self.damage_log[player].clear()
        self.critical = critical

        player2 = player if self_harm else not player

        p1 = self.pokemon[player] # 攻撃側
        p2 = self.pokemon[player2] # 防御側

        move_type = self.move_type(player, move)
        move_class = p1.move_class(move)
        move_power = Pokemon.all_moves[move]['power']

        if move_power == 0:
            return []

        # 補正値
        pl = player2 if move == 'イカサマ' else player 
        r_attack_type = self.attack_type_correction(pl, move)
        r_defence_type = self.defence_type_correction(player, move, self_harm=self_harm)
        r_power = self.power_correction(pl, move, self_harm=self_harm)*power_factor
        r_attack = self.attack_correction(pl, move, self_harm=self_harm)
        r_defence = self.defence_correction(player, move, self_harm=self_harm)
        r_damage = self.damage_correction(player, move, self_harm=self_harm, lethal=lethal)
        #print(f'{move_type=}'),print(f'{r_attack_type=}'),print(f'{r_defence_type=}'),print(f'{r_power=}'),print(f'{r_attack=}'),print(f'{r_defence=}'),print(f'{r_damage=}')

        # 最終威力
        final_power = max(1, round_half_down(move_power*r_power/4096))
        
        # 最終攻撃・ランク補正
        ind = 1
        if move == 'ボディプレス':
            ind = 2
        elif move_class == 'spe':
            ind = 3

        final_attack = self.pokemon[pl].status[ind]
        r_rank = self.pokemon[pl].rank_correction(ind)

        if self.ability(player2, move) == 'てんねん':
            if r_rank > 1:
                r_rank = 1
                self.damage_log[player].append('てんねん AC上昇無視')
        elif self.critical and r_rank < 1:
            r_rank = 1
            self.damage_log[player].append('急所 AC下降無視')

        final_attack = int(final_attack*r_rank)

        if p1.ability == 'はりきり' and move_class == 'phy':
            final_attack = int(final_attack*1.5)
            self.damage_log[player].append('はりきり x1.5')

        final_attack = max(1, round_half_down(final_attack*r_attack/4096))

        # 最終防御・ランク補正
        ind = 2 if move_class == 'phy' or move in Pokemon.move_category['physical'] else 4
        final_defence = p2.status[ind]
        r_rank = 1 if move in Pokemon.move_category['ignore_rank'] else p2.rank_correction(ind)

        if self.ability(player, move) == 'てんねん':
            if r_rank > 1:
                r_rank = 1
                self.damage_log[player].append('てんねん BD上昇無視')
        elif self.critical and r_rank > 1:
            r_rank = 1
            self.damage_log[player].append('急所 BD上昇無視')

        final_defence = int(final_defence*r_rank)

        # 雪・砂嵐補正
        if self.weather() == 'snow' and 'こおり' in p2.types and move_class == 'phy':
            final_defence = int(final_defence*1.5)
            self.damage_log[player].append('ゆき B x1.5')
        elif self.weather() == 'sandstorm' and 'いわ' in p2.types and move_class == 'spe':
            final_defence = int(final_defence*1.5)
            self.damage_log[player].append('すなあらし D x1.5')

        final_defence = max(1, round_half_down(final_defence*r_defence/4096))

        # 最大ダメージ
        max_damage = int(int(int(p1.level*0.4+2)*final_power*final_attack/final_defence)/50+2) 

        #　晴・雨補正
        if self.weather(player2) == 'sunny':
            match move_type:
                case 'ほのお':
                    max_damage = round_half_down(max_damage*1.5)
                    self.damage_log[player].append('はれ x1.5')
                case 'みず':
                    max_damage = round_half_down(max_damage*0.5)
                    self.damage_log[player].append('はれ x0.5')
        elif self.weather(player2) == 'rainy':
            match move_type:
                case 'ほのお':
                    max_damage = round_half_down(max_damage*0.5)
                    self.damage_log[player].append('あめ x0.5')
                case 'みず':
                    max_damage = round_half_down(max_damage*1.5)
                    self.damage_log[player].append('あめ x1.5')

        if p2.last_used_move == 'きょけんとつげき' and player2 == self.action_order[0]:
            max_damage = round_half_down(max_damage*2)
            self.damage_log[player].append('きょけんとつげき x2.0')

        # 急所
        if self.critical:
            max_damage = round_half_down(max_damage*1.5)
            self.damage_log[player].append('急所 x1.5')

        damage = [0]*16
        for i in range(16):
            # 乱数 85%~100%
            damage[i] = int(max_damage*(0.85+0.01*i))
            # 攻撃タイプ補正
            damage[i] = round_half_down(damage[i]*r_attack_type)
            # 防御タイプ補正
            damage[i] = int(damage[i]*r_defence_type)
            # 状態異常補正
            if p1.ailment == 'BRN' and move_class == 'phy' and p1.ability != 'こんじょう' and move != 'からげんき':
                damage[i] = round_half_down(damage[i]*0.5)
                if i == 0:
                    self.damage_log[player].append('やけど x0.5')
            # ダメージ補正
            damage[i] = round_half_down(damage[i]*r_damage/4096)           
            if damage[i] == 0 and r_defence_type*r_damage > 0:
                damage[i] = 1

        return damage

    def lethal(self, player: int, move_list: list[str], critical: bool=False, 
               n_hit:int=5, max_loop: int=10) -> str:
        """相手を瀕死にするまでに最低限必要な攻撃回数と瀕死確率を計算する
        
        Parameters
        ----------
        player: int
            攻撃側のplayer
        
        move_list: list[str]
            攻撃技。要素が2個以上の場合は加算ダメージに対する確定数となる。
        
        critical: bool
            急所判定
        
        n_hit: int
            連続技のヒット数

        max_loop: int
            ダメージ計算の繰り返しの上限

        Returns
        ----------
        p2.damage_text(self.damage_dict, self.lethal_num, self.lethal_prob): str
            'd1~d2 (p1~p2 %) 確n' 形式の文字列。
        """        
        ### 単発ダメージ計算
        moves, damage_dict_list = [], []

        # 加算ダメージ計算
        for move in move_list:
            critical |= move in Pokemon.move_category['critical']
            
            for i in range(self.num_hits(player, move, n=n_hit)):
                if i==0 or move == 'トリプルアクセル':
                    # 1ヒットあたりのダメージを計算
                    oneshot_damage = self.oneshot_damages(player, move, lethal=True, critical=critical, power_factor=i+1)
                    if not oneshot_damage:
                        break

                moves.append(move)

                dict = {}
                for v in oneshot_damage:
                    push(dict, str(v), 1)
                damage_dict_list.append(dict)

            # ターン終了フラグを追加
            moves.append('END')
            damage_dict_list.append({})

        ### リーサル計算
        player2 = not player
        p2 = self.pokemon[player2] # 防御側

        self.damage_dict = {'0': 1} # 1ターン目に与えたダメージ
        self.hp_dict = {str(p2.hp): 1} # 1ターン目終了時の残りHP
        self.lethal_num, self.lethal_prob = 0, 0

        if not moves:
            return ''

        recovery_fruit = ['オレンのみ','オボンのみ','フィラのみ','ウイのみ','マゴのみ','バンジのみ','イアのみ']
        recoverable = p2.item in recovery_fruit and not self.is_nervous(player2)

        hp_dict = {str(p2.hp)+('' if p2.item else '.0'): 1} # 残りHP

        # 瀕死になるまでターンを繰り返す
        for i in range(max_loop):
            self.lethal_num += 1

            # 加算計算
            for (move, damage_dict) in zip(moves, damage_dict_list):
                if move != 'END':
                    newhp_dict, newdamage_dict = {}, {}
                    for hp in hp_dict:
                        for dmg in damage_dict:
                            # ダメージ修正
                            d = int(dmg)
                            if float(hp) == p2.status[0] and self.ability(player2, move) in ['ファントムガード','マルチスケイル']:
                                d = int(d/2)

                            # HPからダメージを引く
                            hp_key = str(int(max(0, float(hp)-d))) + '.0'*(hp[-2:] == '.0')

                            push(newhp_dict, hp_key, hp_dict[hp]*damage_dict[dmg])
                            push(newdamage_dict, str(d), hp_dict[hp]*damage_dict[dmg])

                    hp_dict = newhp_dict.copy()
                    
                    if recoverable:
                        hp_dict = p2.fruit_recovery(hp_dict) # 回復実の判定

                    # 初回のダメージを合計して記録する
                    if i == 0:
                        cross_sum = {}
                        for k1, v1 in self.damage_dict.items():
                            for k2, v2 in newdamage_dict.items():
                                cross_sum[str(int(k1)+int(k2))] = v1 * v2
                        self.damage_dict = cross_sum
                else:
                    # ターン終了時の処理
                    # 砂嵐ダメージ
                    if self.weather() == 'sandstorm' and all(s not in p2.types for s in ['いわ','じめん','はがね']) and \
                        not self.is_overcoat(player2) and p2.ability not in ['すなかき','すながくれ','すなのちから','マジックガード']:
                            hp_dict = offset_hp_keys(hp_dict, -int(p2.status[0]/16))
                            if recoverable:
                                hp_dict = p2.fruit_recovery(hp_dict) # 回復実の判定

                    # 天候に関する特性
                    match self.weather(player2):
                        case 'sunny':
                            if p2.ability in ['かんそうはだ','サンパワー']:
                                hp_dict = offset_hp_keys(hp_dict, -int(p2.status[0]/8))
                                if recoverable:
                                    hp_dict = p2.fruit_recovery(hp_dict) # 回復実の判定
                        case 'rainy':
                            match p2.ability:
                                case 'あめうけざら':
                                    hp_dict = offset_hp_keys(hp_dict, int(p2.status[0]/16))
                                case 'かんそうはだ':
                                    hp_dict = offset_hp_keys(hp_dict, int(p2.status[0]/8))
                        case 'snow':
                            if p2.ability == 'アイスボディ':
                                hp_dict = offset_hp_keys(hp_dict, int(p2.status[0]/16))

                    # グラスフィールド
                    if self.condition['glassfield'] and not self.is_float(player2):
                        hp_dict = offset_hp_keys(hp_dict, int(p2.status[0]/16))

                    # たべのこし系
                    match p2.item:
                        case 'たべのこし':
                            hp_dict = offset_hp_keys(hp_dict, int(p2.status[0]/16))
                        case 'くろいヘドロ':
                            r = 1 if 'どく' in p2.types else -1*(p2.ability != 'マジックガード')
                            hp_dict = offset_hp_keys(hp_dict, int(p2.status[0]/16*r))
                            if r == -1 and recoverable:
                                hp_dict = p2.fruit_recovery(hp_dict) # 回復実の判定

                    # アクアリング・ねをはる
                    h = self.absorbed_value(player, int(p2.status[0]/16), from_enemy=False)
                    if p2.condition['aquaring']:
                        hp_dict = offset_hp_keys(hp_dict, h)
                    if p2.condition['neoharu']:
                        hp_dict = offset_hp_keys(hp_dict, h)

                    # やどりぎのタネ
                    if p2.condition['yadorigi'] and p2.ability != 'マジックガード':
                        hp_dict = offset_hp_keys(hp_dict, -int(p2.status[0]/16))
                        if recoverable:
                            hp_dict = p2.fruit_recovery(hp_dict) # 回復実の判定

                    # 状態異常ダメージ
                    h = 0
                    match p2.ailment * (p2.ability != 'マジックガード'):
                        case 'PSN':
                            if p2.ability == 'ポイズンヒール':
                                h = int(p2.status[0]/8)
                            elif p2.condition['badpoison']:
                                h = -int(p2.status[0]/16*p2.condition['badpoison'])
                                p2.condition['badpoison'] += 1
                            else:
                                h = -int(p2.status[0]/8)
                        case 'BRN':
                            h = -int(p2.status[0]/16)
                    if h:
                        hp_dict = offset_hp_keys(hp_dict, h)
                        if h < 0 and recoverable:
                            hp_dict = p2.fruit_recovery(hp_dict) # 回復実の判定

                    # 呪いダメージ
                    if p2.condition['noroi'] and p2.ability != 'マジックガード':
                        hp_dict = offset_hp_keys(hp_dict, -int(p2.status[0]/4))
                        if recoverable:
                            hp_dict = p2.fruit_recovery(hp_dict) # 回復実の判定

                    # バインドダメージ
                    if p2.condition['bind'] and p2.ability != 'マジックガード':
                        hp_dict = offset_hp_keys(hp_dict, -int(p2.status[0]/10/frac(p2.condition['bind'])))
                        if recoverable:
                            hp_dict = p2.fruit_recovery(hp_dict) # 回復実の判定

                    # しおづけダメージ
                    if p2.condition['shiozuke'] and p2.ability != 'マジックガード':
                        r = 2 if any(t in p2.types for t in ['みず','はがね']) else 1
                        hp_dict = offset_hp_keys(hp_dict, -int(p2.status[0]/8*r))
                        if recoverable:
                            hp_dict = p2.fruit_recovery(hp_dict) # 回復実の判定

                    # 1ターン目のHPを記録
                    if i == 0:
                        self.hp_dict = hp_dict.copy()

                    # 瀕死判定
                    self.lethal_prob = zero_ratio(hp_dict)
                    if self.lethal_prob:
                        break
        
            # 瀕死判定
            if self.lethal_prob:
                break

        return p2.damage_text(self.damage_dict, self.lethal_num, self.lethal_prob)

    # 対戦シミュレーション
    def reset_sim_parameters(self):
        self.command = [None, None]
        self.change_command_history = [[], []]
        self.log = [[], []]
        self.damage_log = [[], []]
        self.speed = [0, 0]                     # 優先度を考慮した行動速度
        self.action_order = [0, 1]        
        self.move = [None, None]
        self.was_valid = [True, True]
        self.damage = [0, 0]                    # 技によるダメージ。連続技の場合は最後のダメージ。
        self.has_changed = [False, False]       # そのターンすでに交代していたらTrue
        self.standby = [True, True]

    def changeable_indexes(self, player: int) -> list[int]:
        """交代可能なポケモンの選出番号を返す"""
        indexes = []
        for i,p in enumerate(self.selected[player]):
            if p.hp and (self.pokemon[player] is None or i != self.current_index(player)):
                indexes.append(i)
        return indexes

    def available_commands(self, player: int, phase: str='battle'):
        """状況{phase}に応じて、{player}が選択可能なコマンドの一覧を返す
        Parameters
        ----------
        player: int
        phase: str
            'battle': ターン開始時。攻撃と交代の両方を選択できる。
            'change': とんぼがえり等によりターンの途中に発生する交代。

        Returns
        ----------
        commands: list[int]
            0~9       : n番目の技を選択
            10~19     : テラスタルして(n-10)番目の技を選択
            20~25     : (n-20)番目に選出したポケモンに交代
            30        : わるあがき (=Battle.STRUGGLE)
            40        : 命令できない (Battle.NO_COMMAND)
        """
        
        p = self.pokemon[player]
        commands = []

        if phase == 'battle':
            if p.inaccessible:
                return [Battle.NO_COMMAND]

            # 技を選択
            for i,move in enumerate(p.moves):
                if not self.unusable_reason(player, move):
                    commands.append(i)

            # テラスタルして技を選択
            if self.can_terastal(player):
                commands += [cmd + 10 for cmd in commands]

            # わるあがき
            if not commands:
                commands = [Battle.STRUGGLE]

        # 交代
        if phase == 'change' or not self.is_caught(player):
            for idx in self.changeable_indexes(player):
                commands.append(20+idx)

        if not commands:
            warnings.warn('No available commands')
        
        return commands

    def change_pokemon(self, player: int, command: int=None, idx: int=None,
                       baton: dict={}, landing=True) -> None:
        """場のポケモンを交代する
        """

        # 控えに戻す
        ability1 = None
        if self.pokemon[player] is not None:
            ability1 = self.pokemon[player].ability
            self.pokemon[player].come_back()

            # フォルムチェンジ
            if self.pokemon[player].name == 'イルカマン(ナイーブ)':
                self.pokemon[player].change_form('イルカマン(マイティ)')
                self.log[player].append('-> マイティフォルム')

                # 観測値も更新
                p = Pokemon.find(self.observed[player], display_name='イルカマン')
                p.change_form('イルカマン(マイティ)')

        # コマンドに変換
        if command is not None:
            pass
        elif idx is not None:
            command = idx + 20
        else:
            if self.reserved_change_commands[player]:
                command = self.reserved_change_commands[player].pop(0)
            else:
                command = self.change_command(player)
            self.change_command_history[player].append(command)
        
        # 交代
        self.pokemon[player] = self.selected[player][command-20]
        self.has_changed[player] = True
        self.log[player].append(f'交代 -> {self.pokemon[player].name}')

        # Breakpoint解除
        self.breakpoint[player] = ''

        # ポケモンの観測
        if Pokemon.find(self.observed[player], name=self.pokemon[player].name) is None:
            self.observed[player].append(Pokemon(self.pokemon[player].name, use_template=False))
            self.observed[player][-1].speed_range = [0, 999]
            #print(f'Player{player}の{self.observed[player][-1].name}を観測')

        # 相手の状態変化を解除
        if self.pokemon[not player] is not None:
            # かがくへんかガス
            if ability1 == 'かがくへんかガス' and not self.pokemon[not player].ability:
                self.pokemon[not player].ability = self.pokemon[not player].org_ability
                self.release_ability(not player)
                self.log[not player].append('かがくへんかガス解除')
            
            # バインド状態
            if self.pokemon[not player].condition['bind']:
                self.pokemon[not player].condition['bind'] = 0
                self.log[player].append('バインド解除')

            # にげられない状態
            if self.pokemon[not player].condition['change_block']:
                self.pokemon[not player].condition['change_block'] = 0
                self.log[player].append('にげられない解除')

        # バトン処理
        if baton:
            if 'sub_hp' in baton:
                self.pokemon[player].sub_hp = baton['sub_hp']
                self.log[player].append(f'継承 みがわり HP{baton["sub_hp"]}')
            if 'rank' in baton:
                self.pokemon[player].rank = baton['rank']
                self.log[player].append(f'継承 ランク {baton["rank"][1:]}')
            for s in list(self.pokemon[player].condition.keys())[:8]:
                if s in baton:
                    self.pokemon[player].condition[s] = baton[s]
                    self.log[player].append(f'継承 {Pokemon.JPN[s]} {baton[s]}')
        
        # 行動順の更新
        self.update_speed_order()

        # 着地時の処理
        if landing:
            self.land(player)
    
    def battle_command(self, player: int) -> int:
        """{player}のターン開始時に呼ばれる方策関数"""
        return random.choice(self.available_commands(player))

    def change_command(self, player: int) -> int:
        """{player}の任意交代時に呼ばれる方策関数"""
        return random.choice(self.available_commands(player, phase='change'))

    def record_command(self):
        """コマンドをログ出力用に記録"""
        self._dump[f'Turn{self.turn - 1}'] = {
            'command': self.command,
            'change_command_history': self.change_command_history
        }

    def dump(self) -> str:
        """ターン処理の履歴をjson形式で返す"""
        return json.dumps(self._dump, ensure_ascii=False)
    
    def num_hits(self, player: int, move: str, n: int=None) -> int:
        """{player}の場のポケモンが{move}を使用したときの技の発動回数を返す"""
        if move not in Pokemon.combo_hit:
            return 1
        
        p1 = self.pokemon[player] # 攻撃側
        n_min, n_max = Pokemon.combo_hit[move][0], Pokemon.combo_hit[move][1]
        
        if n is not None and n_min <= n <= n_max:
            return n

        if n_min != n_max:
            if p1.ability == 'スキルリンク':
                return n_max
            elif p1.item == 'いかさまダイス':
                return n_max - self._random.randint(0, 1)
            elif n_min == 2 and n_max == 5:
                return self._random.choice([2,2,2,3,3,3,4,5])

        return n_max

    def TOD_score(self, player: int, alpha: float=1) -> float:
        """TODスコアを返す。
        このスコアの大きいplayerがTOD判定で勝利する。   
        選出したポケモンが全滅したら0となる。
        対戦シミュレーション用の関数。
        
        Parameters
        ----------
        player: int

        alpha: float
            0~1。生存ポケモン数に対する、残りHP割合の重みづけ。
        """
        n_alive, full_hp, total_hp = 0, 0, 0
        
        for p in self.selected[player]:
            if p is not None:
                full_hp += p.status[0]
                total_hp += p.hp
                if p.hp:
                    n_alive += 1
        
        return n_alive + alpha * total_hp / full_hp

    def winner(self, is_timeup: bool=False, record=False) -> int:
        """試合に勝利したプレイヤーを返す。{is_timeup}=Trueなら時間切れによる判定を行う"""
        winner = None
        TOD_scores = [self.TOD_score(player) for player in range(2)]

        if 0 in TOD_scores or is_timeup:
            winner = TOD_scores.index(max(TOD_scores))
            self.log[winner].append('勝ち')
            self.log[not winner].append('負け')

            # このターンに入力されたコマンドを記録
            if record:
                self.record_command()

        return winner

    def choose_damage(self, player: int, damage_list: list[int]) -> int:
        """乱数により分岐したダメージの中から計算に用いるダメージを選択する"""
        return self._random.choice(damage_list)

    def add_rank(self, player: int, index: int, value: int, rank_list: list[int]=[], 
                 by_enemy: bool=False, can_chain: bool=False) -> list[int]:
        """場のポケモンの能力ランクを変動させる。対戦シミュレーション用の関数。
        Parameters
        ----------
        player: int
            対象のplayer。

        index: int
            変動させる能力番号。
                0,1,2,3,4,5,6,7
                H,A,B,C,D,S,命中,回避

        value: int
            変動量。

        rank_list: list[int]
            indexまたはvalueが0の場合、このリストを参照して能力ランクを変動させる。

        by_enemy: bool
            Trueなら相手による能力変化とみなす。

        can_chain: bool
            Falseならミラーアーマーやものまねハーブによる追加の能力変化が発動しない。
        
        Returns
        ----------
        delta: list[int]
            変動したランクのリスト。
        """
        if (index == 0 or value == 0) and not any(rank_list):
            return []

        if not any(rank_list):
            rank_list = [0]*8
            rank_list[index] = value

        player2 = not player
        p1 = self.pokemon[player] # ランク変化する側
        p2 = self.pokemon[player2] # しかけた側
        delta = [0]*8
        reflection = [0]*8

        for i,v in enumerate(rank_list):
            if i == 0 or v == 0:
                continue
            
            if p1.item == 'クリアチャーム' and v < 0 and by_enemy:
                if self.log[player][-1] != p1.item:
                    self.log[player].append(p1.item)
                continue

            if p1.ability == 'あまのじゃく':
                v *= -1

            if p1.rank[i]*v/abs(v) == 6:
                continue
            
            if v < 0 and by_enemy:
                if self.condition['whitemist'][player]:
                    if self.log[player][-1] != Pokemon.JPN['whitemist']:
                        self.log[player].append(Pokemon.JPN['whitemist'])
                    continue
                
                match p1.ability:
                    case 'クリアボディ' | 'しろいけむり' | 'メタルプロテクト':
                        if self.log[player][-1] != p1.ability:
                            self.log[player].append(p1.ability)
                        continue
                    case 'フラワーベール':
                        if self.condition['sunny']:
                            if self.log[player][-1] != p1.ability:
                                self.log[player].append(p1.ability)
                            continue
                    case 'かいりきバサミ':
                        if i == 1:
                            if self.log[player][-1] != p1.ability:
                                self.log[player].append(p1.ability)
                            continue
                    case 'はとむね':
                        if i == 2:
                            if self.log[player][-1] != p1.ability:
                                self.log[player].append(p1.ability)
                            continue
                    case 'しんがん' | 'するどいめ':
                        if i == 6:
                            if self.log[player][-1] != p1.ability:
                                self.log[player].append(p1.ability)
                            continue
                    case 'ミラーアーマー':
                        reflection[i] = v
                        continue
                            
            prev = p1.rank[i]
            p1.rank[i] = max(-6, min(6, prev + v*(2 if p1.ability == 'たんじゅん' else 1)))
            delta[i] = p1.rank[i] - prev

        if any(reflection) and not can_chain and self.add_rank(player2, 0, 0, rank_list=reflection, can_chain=True):
            self.log[player].append(p1.ability)

        if not any(delta):
            return []

        p1.rank_dropped = any(v < 0 for v in delta)

        self.log[player].append(Pokemon.rank2str(delta))

        if any([min(0, v) for v in delta]):
            match p1.ability * by_enemy:
                case 'かちき':
                    if self.add_rank(player, 3, +2):
                        self.log[player].insert(-1, p1.ability)
                case 'まけんき':
                    if self.add_rank(player, 1, +2):
                        self.log[player].insert(-1, p1.ability)
        
        if any(pos_delta := [max(0, v) for v in delta]) and not can_chain:
            if p2.ability == 'びんじょう' and self.add_rank(player2, 0, 0, rank_list=pos_delta, can_chain=True):
                self.log[player2].insert(-1, p2.ability)
            if p2.item == 'ものまねハーブ' and self.add_rank(player2, 0, 0, rank_list=pos_delta, can_chain=True):
                self.log[player2].insert(-1, p2.item)
                self.consume_item(player2)

        return delta

    def add_hp(self, player: int, value: int, move: str='') -> bool:
        """場のポケモンのHPを変動させる。対戦シミュレーション用の関数。

        Parameters
        ----------
        player: int
            対象のplayer。

        value: int
            HP変動量。

        move: str
            指定された場合はmoveによる変動とみなす。
        
        Returns
        ----------
        : bool
            HPが変動したらTrue。
        """
        p = self.pokemon[player]

        if value == 0:
            return False
        
        # 回復
        elif value > 0:
            if p.hp == p.status[0] or (p.condition['healblock'] and move != 'いたみわけ'):
                return False
            else:
                prev = p.hp
                p.hp = min(p.status[0], p.hp + value)
                self.log[player].append(f'HP +{p.hp - prev}')

        # ダメージ
        else:
            if p.hp == 0 or (not move and p.ability == 'マジックガード'):
                return False

            prev = p.hp
            p.hp = max(0, p.hp + value)
            self.log[player].append(f'HP {p.hp - prev}')

            if move != 'わるあがき' and prev >= p.status[0]/2 and p.hp <= p.status[0]/2:
                p.berserk_triggered = True

            # 回復実の判定
            if p.hp and not self.is_nervous(player) and p.condition['healblock'] == 0 and \
                move not in ['やきつくす','ついばむ','むしくい']:
                match p.item:
                    case 'オレンのみ' | 'オボンのみ':
                        if p.hp <= p.status[0]/2:
                            self.consume_item(player)
                    case 'フィラのみ' | 'ウイのみ' | 'マゴのみ' | 'バンジのみ' | 'イアのみ':
                        if p.hp/p.status[0] <= (0.5 if p.ability == 'くいしんぼう' else 0.25):
                            self.consume_item(player)
        
        # HP割合の観測
        Pokemon.find(self.observed[player], name=self.pokemon[player].name).hp_ratio = p.hp_ratio

        return True

    def set_condition(self, player: int, condition: str, move: str='') -> bool:
        """場のポケモンの状態を変更する。対戦シミュレーション用の関数。

        Parameters
        ----------
        player: int
            対象のplayer。

        condition: str
            変更する状態。

        move: str
            指定された場合はmoveによる変動とみなす。
        
        Returns
        ----------
        : bool
            変更できたらTrue。
        """
        player2 = not player
        p1 = self.pokemon[player]
        p2 = self.pokemon[player2]

        if p1.condition[condition]:
            return False

        match condition:
            case 'confusion':
                if p1.ability == 'マイペース':
                    return False
                else:
                    p1.condition['confusion'] = self._random.randint(2,5)
                    self.log[player].append('こんらん')
                    return True

            case 'nemuke':
                if  p1.ailment or self.condition['safeguard'][player] or \
                    p1.ability in ['ふみん','やるき','スイートベール','きよめのしお','ぜったいねむり','リミットシールド'] or \
                    (p1.ability == 'リーフガード' and self.weather() == 'sunny') or \
                    (p1.ability == 'フラワーベール' and 'くさ' in p1.types) or \
                    (self.field() == 'elecfield' and not self.is_float(player)):
                    return False
                else:
                    p1.condition['nemuke'] = 2
                    return True

            case 'meromero':
                if p1.sex*p2.sex != -1 or self.ability(player, move) in ['アロマベール','どんかん']:
                    return False
                else:
                    p1.condition['meromero'] = 1
                    self.log[player].append('メロメロ')

                    if p1.item == 'あかいいと' and self.set_condition(player2, 'meromero'):
                        self.log[player].insert(-1, 'あかいいと発動')
    
    def consume_item(self, player: int):
        """{player}の場のポケモンの持ち物を消費する。対戦シミュレーション用の関数"""
        player2 = not player
        p1 = self.pokemon[player]
        p2 = self.pokemon[player2]

        if not p1.item:
            return

        r_fruit = 2 if p1.ability == 'じゅくせい' else 1
        p1.item, p1.lost_item, item = '', p1.item, p1.item
        self.log[player].append(f'{item}消費') 

        # アイテムの観測
        p_obs = Pokemon.find(self.observed[player], name=self.pokemon[player].name)
        p_obs.item, p_obs.lost_item = p1.item, p1.lost_item

        # アイテムの効果発動
        match item:
            case 'エレキシード' | 'グラスシード':
                self.add_rank(player, 2, +1)
            case 'サイコシード' | 'ミストシード':
                self.add_rank(player, 4, +1)
            case 'からぶりほけん':
                self.add_rank(player, 5, +2)
            case 'じゃくてんほけん':
                self.add_rank(player, 0, 0, [0,2,0,2])
            case 'しろいハーブ':
                p1.rank = [max(0,v) for v in p1.rank]
            case 'のどスプレー':
                self.add_rank(player, 3, +1)
            case 'パワフルハーブ':
                p1.inaccessible = 0
            case 'ブーストエナジー':
                p1.energy_boost()
                p1.BE_activated = True
                self.log[player].append(f'{Pokemon.status_label[p1.boost_index]}上昇')
            case 'メンタルハーブ':
                for s in ['meromero','encore','kanashibari','chohatsu','healblock']:
                    if p1.condition[s]:
                        p1.condition[s] = 0
                        self.log[player].append(f'{Pokemon.JPN[s]}解除')
                        break
            case 'ルームサービス':
                self.add_rank(player, 5, -1)
            case 'レッドカード':
                if p2.is_blowable():
                    self.change_pokemon(player2)
            case 'じゅうでんち' | 'ゆきだま':
                self.add_rank(player, 1, +1)
            case 'きゅうこん' | 'ひかりごけ':
                self.add_rank(player, 3, +1)
            case 'オレンのみ':
                self.add_hp(player, 10*r_fruit)
            case 'オボンのみ' | 'ナゾのみ':
                self.add_hp(player, int(p1.status[0]/4)*r_fruit)
            case 'フィラのみ' | 'ウイのみ' | 'マゴのみ' | 'バンジのみ' | 'イアのみ':
                self.add_hp(player, int(p1.status[0]/3)*r_fruit)
            case 'ヒメリのみ':
                ind = p1.pp.index(0) if 0 in p1.pp else 0
                p1.pp[ind] = min(Pokemon.all_moves[p1.moves[ind]]['pp'], 10*r_fruit)
                self.log[player].append(f'{p1.moves[ind]} PP {p1.pp[ind]}')
            case 'カゴのみ' | 'クラボのみ' | 'チーゴのみ' | 'ナナシのみ' | 'モモンのみ' | 'ラムのみ':
                self.set_ailment(player, '')
            case 'キーのみ':
                p1.condition['confusion'] = 0
                self.log[player].append(f'こんらん解除')
            case 'チイラのみ':
                self.add_rank(player, 1, r_fruit)
            case 'リュガのみ' | 'アッキのみ':
                self.add_rank(player, 2, r_fruit)
            case 'ヤタピのみ':
                self.add_rank(player, 3, r_fruit)
            case 'ズアのみ' | 'タラプのみ':
                self.add_rank(player, 4, r_fruit)
            case 'カムラのみ':
                self.add_rank(player, 5, r_fruit)
            case 'サンのみ':
                p1.condition['critical'] = 2
                self.log[player].append(f"急所ランク+{p1.condition['critical']}")
            case 'スターのみ':
                self.add_rank(player, self._random.choice([i for i in range(1,6) if p1.rank[i] < 6]), r_fruit)
            case 'ジャポのみ' | 'レンブのみ':
                self.add_hp(player2, -int(self.pokemon[player2].status[0]/8*r_fruit))

        if p1.ability == 'かるわざ':
            self.log[player].append(p1.ability) 
            p1.ability += '+'

        if item[-2:] == 'のみ':
            match p1.ability:
                case 'はんすう':
                    p1.ability = 'はんすう+'
                    self.log[player].append('はんすう起動') 
                    p_obs.ability = p1.ability
                case 'ほおぶくろ':
                    if self.add_hp(player, int(p1.status[0]/3)):
                        self.log[player].insert(-1, p1.ability) 
                        p_obs.ability = p1.ability
        
    def absorbed_value(self, player: int, raw_amount: int, from_enemy: bool=True):
        """HP吸収量に補正を適用して返す。対戦シミュレーション用の関数。
        {from_enemy}=Trueなら相手からHPを吸収したとみなす。
        """
        r = 5324/4096 if self.pokemon[player].item == 'おおきなねっこ' else 1
        if from_enemy and self.pokemon[not player].ability == 'ヘドロえき':
            r = -r
        return round_half_up(raw_amount*r)

    def land(self, player: int):
        """{player}のポケモンが場に出たときの処理を行う。対戦シミュレーション用の関数"""
        p1 = self.pokemon[player]

        # 設置物の判定
        if p1.item != 'あつぞこブーツ':
            if self.condition['stealthrock'][player]:
                d = -int(p1.status[0]/8*self.defence_type_correction(not player, 'ステルスロック'))
                if self.add_hp(player, d):
                    self.log[player].insert(-1, 'ステルスロック')
            
            if not self.is_float(player):
                if self.condition['makibishi'][player]:
                    d = -int(p1.status[0]/(10-2*self.condition['makibishi'][player]))
                    if self.add_hp(player, d):
                        self.log[player].insert(-1, 'まきびし')
            
                if self.condition['dokubishi'][player]:
                    if 'どく' in p1.types:
                        self.condition['dokubishi'][player] = 0
                        self.log[player].append('どくびし解除')
                    elif self.set_ailment(player, 'PSN', badpoison=(self.condition['dokubishi'][player] == 2)):
                        self.log[player].append('どくびし接触')
            
                if self.condition['nebanet'][player]:
                    if self.add_rank(player, 5, -1, by_enemy=True):
                        self.log[player].insert(-1, 'ねばねばネット')

        # 生死判定
        if not p1.hp:
            return

        # 特性の発動
        for pl in [player, not player]:
            if not self.pokemon[pl].has_protected_ability():
                if self.pokemon[not pl].ability == 'かがくへんかガス' and self.pokemon[pl].item != 'とくせいガード':
                    self.pokemon[pl].ability = ''
                    self.log[pl].append('かがくへんかガス 特性無効')
                    break
                elif self.pokemon[pl].ability == 'トレース' and \
                    self.pokemon[not pl].ability not in Pokemon.ability_category['unreproducible']:
                    self.pokemon[pl].ability = self.pokemon[not pl].ability
                    self.log[pl].append(f'トレース -> {self.pokemon[not pl].ability}')
            
            self.release_ability(pl)

        # 即時発動アイテムの判定 (着地時)
        for pl in range(2):
            self.use_immediate_item(pl)

    def unusable_reason(self, player: int, move: str) -> str:
        """{player}の場のポケモンが{move}を選択できない状態であればその理由を返す。対戦シミュレーション用の関数"""
        p = self.pokemon[player]
        if move == 'わるあがき':
            return ''
        if not move:
            return 'Empty move'
        # PP切れ
        if p.pp[p.moves.index(move)] == 0:
            return 'PP切れ'
        # アンコール
        if p.condition['encore'] and move != p.last_pp_move:
            return 'アンコール状態'
        # かいふくふうじ
        if p.condition['healblock'] and (move in Pokemon.move_category['heal'] or move in Pokemon.move_value['drain']):
            return 'かいふくふうじ状態'
        # かなしばり
        if p.condition['kanashibari'] and move == p.last_pp_move:
            return 'かなしばり状態'
        # じごくづき
        if p.condition['jigokuzuki'] and move in Pokemon.move_category['sound']:
            return 'じごくづき状態'
        # ちょうはつ
        if p.condition['chohatsu'] and 'sta' in Pokemon.all_moves[move]['class']:
            return 'ちょうはつ状態'
        # 連発できない技
        if move == p.last_used_move and move in Pokemon.move_category['unrepeatable']:
            return '連発'
        # こだわり
        if p.fixed_move and move != p.fixed_move:
            return 'こだわり状態'
        # とつげきチョッキ
        if p.item == 'とつげきチョッキ' and Pokemon.all_moves[move]['class'] not in ['phy','spe']:
            return 'とつげきチョッキ'

        return ''
    
    def is_caught(self, player: int) -> bool:
        """{player}の場のポケモンが交代できない状態ならTrueを返す。対戦シミュレーション用の関数"""
        player2 = not player
        p1 = self.pokemon[player]
        p2 = self.pokemon[player2]
        p1_types = p1.types

        if 'ゴースト' in p1_types or p1.ability == 'にげあし' or p1.item == 'きれいなぬけがら':
            return False
        
        if p1.condition['change_block'] or p1.condition['bind']:
            return True
        
        match p2.ability:
            case 'ありじごく':
                return not self.is_float(player)
            case 'かげふみ':
                return p1.ability != 'かげふみ'
            case 'じりょく':
                return 'はがね' in p1_types
            
        return False

    def can_move_affects(self, player: int, move: str) -> bool:
        """{player}の場のポケモンが{move}を使用するとき、追加効果が発生しうるならTrueを返す。対戦シミュレーション用の関数"""
        player2 = not player
        p1 = self.pokemon[player]
        p2 = self.pokemon[player2]
        return p1.ability != 'ちからずく' and p2.item != 'おんみつマント' and self.ability(player2, move) != 'りんぷん'

    def release_ability(self, player: int) -> None:
        """{player}の場のポケモンの特性を起動する"""
        player2 = not player
        p1 = self.pokemon[player] # 場に出た側
        p2 = self.pokemon[player2] # 相手側

        match p1.ability:
            case 'ひでり' | 'ひひいろのこどう':
                if self.set_weather(player, 'sunny'):
                    self.log[player].insert(-1, p1.ability)
            case 'あめふらし':
                if self.set_weather(player, 'rainy'):
                    self.log[player].insert(-1, p1.ability)
            case 'ゆきふらし':
                if self.set_weather(player, 'snow'):
                    self.log[player].insert(-1, p1.ability)
            case 'すなおこし':
                if self.set_weather(player, 'sandstorm'):
                    self.log[player].insert(-1, p1.ability)
            case 'エレキメイカー' | 'ハドロンエンジン':
                if self.set_field(player, 'elecfield'):
                    self.log[player].insert(-1, p1.ability)
            case 'グラスメイカー':
                if self.set_field(player, 'glassfield'):
                    self.log[player].insert(-1, p1.ability)
            case 'サイコメイカー':
                if self.set_field(player, 'psycofield'):
                    self.log[player].insert(-1, p1.ability)
            case 'ミストメイカー':
                if self.set_field(player, 'mistfield'):
                    self.log[player].insert(-1, p1.ability)
            case 'クォークチャージ':
                if self.condition['elecfield']:
                    p1.energy_boost()
                    self.log[player].append(f'{Pokemon.status_label[p1.boost_index]}上昇')
            case 'こだいかっせい':
                if self.weather() == 'sunny':
                    p1.energy_boost()
                    self.log[player].append(f'{Pokemon.status_label[p1.boost_index]}上昇')
            case 'いかく':
                if p2.ability == 'ばんけん' and self.add_rank(player2, 1, +1, by_enemy=True):
                    self.log[player2].insert(-1, p2.ability)
                elif p2.ability in ['きもったま','せいしんりょく','どんかん','マイペース']:
                    self.log[player2].append(f'いかく無効 {p2.ability}')
                elif self.add_rank(player2, 1, -1, by_enemy=True):
                    self.log[player].append(p1.ability)
            case 'おもかげやどし':
                ind = {'くさ':5, 'ほのお':1, 'みず':4, 'いわ':2}
                if self.add_rank(player, ind[p1.types[0]], +1):
                    self.log[player].insert(-1, p1.ability)
            case 'かぜのり':
                if self.condition['oikaze'][0] and self.add_rank(player, 1, +1):
                    self.log[player].insert(-1, p1.ability)
            case 'かんろなみつ':
                p1.ability += '+'
                if self.add_rank(player2, 7, -1):
                    self.log[player].insert(-1, p1.ability)
            case 'ダウンロード':
                eff_b = int(p2.status[2]*p2.rank_correction(2))
                eff_d = int(p2.status[4]*p2.rank_correction(4))
                if self.add_rank(player, 1+2*int(eff_b > eff_d), +1):
                    self.log[player].insert(-1, p1.ability)
            case 'バリアフリー':
                removed = False
                for s in ['reflector','lightwall']:
                    if any(self.condition[s]):
                        self.condition[s] = [0, 0]
                        removed = True
                if removed:
                    self.log[player].append(p1.ability)
            case 'ふくつのたて':
                p1.ability += '+'
                if self.add_rank(player, 2, +1):
                    self.log[player].insert(-1, p1.ability)
            case 'ふとうのけん':
                p1.ability += '+'
                if self.add_rank(player, 1, +1):
                    self.log[player].insert(-1, p1.ability)

    def set_ailment(self, player: int, ailment: str, move: str='',
                    badpoison: bool=False, safeguard: bool=True) -> bool:
        """場のポケモンの状態異常を変更する。
        Parameters
        ----------
        player: int
            対象のplayer。
        
        ailment:  str
            状態異常。{ailment}=''なら状態異常を解除する。
        
        move: str
            指定されるとmoveによる変更とみなす。

        badpoison: bool
            Trueならもうどくにする。

        safeguard: bool
            Trueならしんぴのまもりを考慮する。

        Returns
        ----------
        :bool
            状態異常を変更できた場合はTrue。
        """
        player2 = not player
        p1 = self.pokemon[player] # 状態異常になる側
        p2 = self.pokemon[player2] # 変化技をかける側
        type1 = p1.types
        ability1 = self.ability(player, move)

        if not ailment:
            if p1.ailment:
                self.log[player].append(f'{Pokemon.JPN[p1.ailment]}解除')
                p1.ailment = ''
                return True
            else:
                return False

        # すべての状態異常を無効にする条件
        if ability1 in ['きよめのしお', 'ぜったいねむり'] or \
            (ability1 == 'リーフガード' and self.weather() == 'sunny') or \
            (ability1 == 'フラワーベール' and 'くさ' in type1):
            self.log[player].append(ability1)
            return False
        
        if self.condition['mistfield'] and not self.is_float(player):
            self.log[player].append(Pokemon.JPN['mistfield'])
            return False

        if move == 'ねむる':
            if p1.ailment == 'SLP':
                return False
        elif p1.ailment or (safeguard and self.condition['safeguard'][player]):
                return False

        # 特定の状態異常を無効にする条件
        match ailment:
            case 'PSN':
                if ability1 in ['めんえき','パステルベール']:
                    self.log[player].append(ability1)
                    return False
                if any(t in type1 for t in ['どく','はがね']) and not (p2.ability == 'ふしょく' and move and 'sta' in Pokemon.all_moves[move]['class']):
                    return False
            case 'PAR':
                if 'でんき' in type1:
                    return False
                if ability1 == 'じゅうなん':
                    self.log[player].append(ability1)
                    return False
                if move == 'でんじは' and 'じめん' in type1:
                    return False
            case 'BRN':
                if 'ほのお' in type1:
                    return False
                if ability1 in ['すいほう','ねつこうかん','みずのベール']:
                    self.log[player].append(ability1)
                    return False
            case 'SLP':
                if ability1 in ['スイートベール','やるき','ふみん']:
                    self.log[player].append(ability1)
                    return False
                if self.condition['elecfield'] and not self.is_float(player):
                    return False
            case 'FLZ':
                if 'こおり' in type1:
                    return False
                if ability1 == 'マグマのよろい':
                    self.log[player].append(ability1)
                    return False
                if self.weather() == 'sunny':
                    return False

        p1.ailment = ailment
        self.log[player].append(Pokemon.JPN[p1.ailment])
        
        match p1.ailment:
            case 'PSN':
                p1.condition['badpoison'] = int(badpoison)
                if p2.ability == 'どくくぐつ' and move and self.set_condition(player, 'confusion'):
                    self.log[player].insert(-1, p2.ability)
            case 'SLP':
                p1.sleep_count = 3 if move == 'ねむる' else self._random.randint(2,4)
                p1.condition['nemuke'] = 0
                p1.inaccessible = 0

        if p1.ability == 'シンクロ' and move not in['','ねむる'] and self.set_ailment(player2, ailment):
            self.log[player].insert(-1, p1.ability)

        return True

    def set_weather(self, player: int, weather: str) -> bool:
        """{player}の場のポケモンに天候を変更させる。対戦シミュレーション用の関数"""
        current_weather = [s for s in Pokemon.weathers if self.condition[s]] or ['']
        current_weather = current_weather[0]
        if weather == current_weather:
            return False

        turn = 8 if weather and self.pokemon[player].item == Pokemon.stone_weather[weather] else 5
        for s in Pokemon.weathers:
            if s == weather:
                self.condition[s] = turn
            else:
                self.condition[s] = 0

        if weather:
            self.log[player].append(f'{Pokemon.JPN[weather]} {self.condition[weather]}ターン')
        else:
            self.log[player].append(f'{Pokemon.JPN[current_weather]}解除')

        for pl,p in enumerate(self.pokemon):
            if p.ability == 'こだいかっせい':
                match weather:
                    case 'sunny':
                        if p.boost_index == 0:
                            p.energy_boost()
                            self.log[pl].append(f'{Pokemon.status_label[p.boost_index]}上昇')
                    case '':
                        if not p.BE_activated:
                            p.energy_boost(False)

        return True

    def set_field(self, player: int, field: str) -> bool:
        """{player}の場のポケモンにフィールドを変更させる。対戦シミュレーション用の関数"""
        current_field = [s for s in Pokemon.fields if self.condition[s]] or ['']
        current_field = current_field[0]
        if field == current_field:
            return False

        turn = 8 if field and self.pokemon[player].item == 'グランドコート' else 5
        for s in Pokemon.fields:
            if s == field:
                self.condition[s] = turn
            else:
                self.condition[s] = 0

        if field:
            self.log[player].append(f'{Pokemon.JPN[field]} {self.condition[field]}ターン')
        else:
            self.log[player].append(f'{Pokemon.JPN[current_field]}解除')

        for pl,p in enumerate(self.pokemon):
            if p.ability == 'クォークチャージ':
                match field:
                    case 'elecfield':
                        if p.boost_index == 0:
                            p.energy_boost()
                            self.log[pl].append(f'{Pokemon.status_label[p.boost_index]}上昇')
                    case '':
                        if not p.BE_activated:
                            p.energy_boost(False)
                            
        return True

    def use_immediate_item(self, player: int) -> str:
        """{player}の場のポケモンのアイテムが発動可能であれば発動し、そのアイテム名を返す。対戦シミュレーション用の関数"""
        p = self.pokemon[player]
        triggered = False
        
        match p.item:
            case 'エレキシード':
                triggered = self.condition['elecfield']
            case 'グラスシード':
                triggered = self.condition['glassfield']
            case 'サイコシード':
                triggered = self.condition['psycofield']
            case 'ミストシード':
                triggered = self.condition['mistfield']
            case 'しろいハーブ':
                triggered = any(v < 0 for v in p.rank)
            case 'ルームサービス':
                triggered = bool(self.condition['trickroom'])
            case 'ブーストエナジー':
                match p.ability:
                    case 'クォークチャージ':
                        triggered = self.condition['elecfield'] == 0
                    case 'こだいかっせい':
                        triggered = self.condition['sunny'] == 0
            case 'メンタルハーブ':
                triggered = p.condition['meromero'] + p.condition['encore'] + p.condition['kanashibari'] + \
                    p.condition['chohatsu'] + p.condition['healblock']
        
        # 木の実
        if not self.is_nervous(player):
            match p.item:
                case 'ヒメリのみ':
                    triggered = 0 in [pp for (i,pp) in enumerate(p.pp) if p.moves[i]]
                case 'カゴのみ':
                    triggered = p.ailment == 'SLP'
                case 'キーのみ':
                    triggered = p.condition['confusion']
                case 'クラボのみ':
                    triggered = p.ailment == 'PAR'
                case 'チーゴのみ':
                    triggered = p.ailment == 'BRN'
                case 'ナナシのみ':
                    triggered = p.ailment == 'FLZ'
                case 'モモンのみ':
                    triggered = p.ailment == 'PSN'
                case 'ラムのみ':
                    triggered = p.ailment
                case 'チイラのみ':
                    triggered = p.hp/p.status[0] <= (0.5 if p.ability == 'くいしんぼう' else 0.25) and p.rank[1] < 6
                case 'リュガのみ':
                    triggered = p.hp/p.status[0] <= (0.5 if p.ability == 'くいしんぼう' else 0.25) and p.rank[2] < 6
                case 'ヤタピのみ':
                    triggered = p.hp/p.status[0] <= (0.5 if p.ability == 'くいしんぼう' else 0.25) and p.rank[3] < 6
                case 'ズアのみ':
                    triggered = p.hp/p.status[0] <= (0.5 if p.ability == 'くいしんぼう' else 0.25) and p.rank[4] < 6
                case 'カムラのみ':
                    triggered = p.hp/p.status[0] <= (0.5 if p.ability == 'くいしんぼう' else 0.25) and p.rank[5] < 6
                case 'サンのみ':
                    triggered = p.hp/p.status[0] <= (0.5 if p.ability == 'くいしんぼう' else 0.25) and p.condition['critical'] == 0
                case 'スターのみ':
                    triggered = p.hp/p.status[0] <= (0.5 if p.ability == 'くいしんぼう' else 0.25) and any(v<6 for v in p.rank[1:6])
                
        if triggered:
            self.consume_item(player)
            return p.item

    def hit_probability(self, player: int, move: str) -> int:
        """{player}の場のポケモンが{move}を使用するときの命中率[%]を返す。対戦シミュレーション用の関数"""
        player2 = not player
        p1 = self.pokemon[player] # 攻撃側
        p2 = self.pokemon[player2] # 防御側
        ability2 = self.ability(player2, move)

        # 必中効果
        if p1.lockon or 'ノーガード' in [p1.ability, ability2] or \
            (self.weather(player2) == 'rainy' and move in Pokemon.move_category['rainy_hit']) or \
            (self.weather() == 'snow' and move == 'ふぶき') or \
            (move == 'どくどく' and 'どく' in p1.types):
            return 1
        
        # 隠れる技
        match p2.hide_move:
            case 'あなをほる':
                if move not in ['じしん','マグニチュード']:
                    return 0
            case 'そらをとぶ' | 'とびはねる':
                if move not in ['かぜおこし','かみなり','たつまき','スカイアッパー','うちおとす','ぼうふう','サウザンアロー']:
                    return 0
            case 'ダイビング':
                if move not in ['なみのり','うずしお']:
                    return 0

        if move in Pokemon.move_category['one_ko']:
            return 0.2 if move == 'ぜったいれいど' and 'こおり' not in p1.types else 0.3
        
        # 技の命中率
        prob = Pokemon.all_moves[move]['hit']

        if self.weather(player) == 'sunny' and move in ['かみなり','ぼうふう']:
            prob *= 0.5
        if ability2 == 'ミラクルスキン' and 'sta' in Pokemon.all_moves[move]['class'] and Pokemon.all_moves[move]['hit'] <= 100:
            prob = min(prob, 50)

        # 命中補正
        m = 4096

        if self.condition['gravity']:
            m = round_half_up(m*6840/4096)

        match p1.ability:
            case 'はりきり':
                if Pokemon.all_moves[move]['class'] == 'phy':
                    m = round_half_up(m*3277/4096)
            case 'ふくがん':
                m = round_half_up(m*5325/4096)
            case 'しょうりのほし':
                m = round_half_up(m*4506/4096)

        match ability2:
            case 'ちどりあし':
                if p2.condition['confusion']:
                    m = round_half_up(m*0.5)
            case 'すながくれ':
                if self.weather() == 'sandstorm':
                    m = round_half_up(m*3277/4096)
            case 'ゆきがくれ':
                if self.weather() == 'snow':
                    m = round_half_up(m*3277/4096)
        
        match p1.item:
            case 'こうかくレンズ':
                m = round_half_up(m*4505/4096)
            case 'フォーカスレンズ':
                if player == self.action_order[-1]:
                    m = round_half_up(m*4915/4096)
        
        if p2.item in ['のんきのおこう','ひかりのこな']:
            m = round_half_up(m*3686/4096)

        # ランク補正
        delta = p1.rank[6]*(ability2 != 'てんねん')
        if p1.ability not in ['しんがん','てんねん','するどいめ','はっこう'] and move not in Pokemon.move_category['ignore_rank']:
            delta -= p2.rank[7] 
        delta = max(-6, min(6, delta))
        r = (3+delta)/3 if delta >=0 else 3/(3-delta)

        #print(int(round_half_down(prob*m/4096)*r)/100)
        return int(round_half_down(prob*m/4096)*r)/100

    def critical_probability(self, player: int, move: str) -> float:
        """{player}の場のポケモンが{move}を使用するときの急所確率を返す"""
        player2 = not player
        p1 = self.pokemon[player] # 攻撃側
        p2 = self.pokemon[player2] # 防御側

        if self.ability(player2, move) in ['シェルアーマー','カブトアーマー'] or move in Pokemon.move_category['one_ko']:
            return 0
                
        m = p1.condition['critical']
        match p1.ability:
            case 'きょううん':
                m += 1
            case 'ひとでなし':
                if p2.ailment == 'PSN':
                    m += 3
        if p1.item in ['するどいツメ','ピントレンズ']:
            m += 1
        match move:
            case move if move in Pokemon.move_category['critical']:
                m += 3
            case move if move in Pokemon.move_category['semi_critical']:
                m += 1

        #print(1/24*(m==0) + 0.125*(m==1) + 0.5*(m==2) + 1*(m>=3))
        return 1/24*(m==0) + 0.125*(m==1) + 0.5*(m==2) + 1*(m>=3)

    def move_speed(self, player: int, move: str, random=True) -> int:
        """<player>の場のポケモンが<move>を使うときの行動速度を返す"""
        speed = 0

        p = self.pokemon[player]

        if move in Pokemon.move_priority:
            speed += 10*Pokemon.move_priority[move]
        
        match p.ability:
            case 'いたずらごころ':
                if 'sta' in Pokemon.all_moves[move]['class']:
                    speed += 10
                    self.log[player].append(p.ability)
            case 'はやてのつばさ':
                if p.hp == p.status[0] and Pokemon.all_moves[move]['type'] == 'ひこう':
                    speed += 10
                    self.log[player].append(p.ability)
            case 'ヒーリングシフト':
                if move in Pokemon.move_category['heal'] or move in Pokemon.move_value['drain']:
                    speed += 30
                    self.log[player].append(p.ability)

        if move == 'グラススライダー' and self.condition['glassfield']:
            speed += 10

        # 下位優先度 (1e0)
        if p.ability == 'きんしのちから' and 'sta' in Pokemon.all_moves[move]['class']:
            speed -= 1
            self.log[player].append(p.ability)
        elif p.ability == 'クイックドロウ' and random and self._random.random() < 0.3:
            speed += 1
            self.log[player].append(p.ability)
        elif p.item == 'せんせいのツメ' and random and self._random.random() < 0.2:
            speed += 1
            self.log[player].append(f'{p.item}発動')
        elif p.item == 'イバンのみ' and p.hp/p.status[0] <= (0.5 if p.ability == 'くいしんぼう' else 0.25):
            speed += 1
            self.consume_item(player)
        else:
            if p.ability == 'あとだし':
                speed -= 1
                self.log[player].append(p.ability)
            if p.item in ['こうこうのしっぽ','まんぷくおこう']:
                speed -= 1
                self.log[player].append(p.item)        

        return speed
    
    def update_speed_order(self) -> bool:
        """素早さ順を更新する。対戦シミュレーション用の関数"""
        if not all(self.pokemon):
            return False
        
        # 素早さを取得
        speeds = []
        for player in range(2):
            speeds.append(self.eff_speed(player))
            if self.condition['trickroom']:
                speeds[player] = 1/speeds[player]
        
        # 同速判定
        if speeds[0] == speeds[1]:
            player = self._random.randint(0,1)
            speeds[player] += 1
            self.log[player].append('同速+1')

        self.speed_order = [speeds.index(max(speeds)), speeds.index(min(speeds))]

        return True

    def complement_pokemon(self, pokemon) -> None:
        """ポケモンの情報を補完する"""
        # 技の補完
        if not pokemon.moves:
            if pokemon.name in Pokemon.home:
                pokemon.add_move(Pokemon.home[pokemon.name]['move'][0][0])
            else:
                pokemon.add_move('テラバースト')

    def complement_move(self, player: int) -> str:
        """相手の行動が開示されていない場合に呼ばれ、{player}が選択した技を返す"""
        available_moves = []
        for cmd in self.available_commands(player):
            if cmd >= 10:
                break
            available_moves.append(self.pokemon[player].moves[cmd])
        return random.choice(available_moves)

    def complement_change_command(self, player: int) -> int:
        """相手の行動が開示されていない場合に呼ばれ、{player}が選択した交代コマンドを返す"""
        return 20 + random.choice(self.changeable_indexes(player))

    def clone(self, player: int=None):
        """インスタンスを複製する
        
        {player}を指定すると、そのプレイヤー視点に相当するように情報を隠蔽する
            1. 相手の選出情を観測値に置き換える
            2. 相手が後手かつ未行動であれば、相手のコマンドを補完する
        """

        battle = deepcopy(self)
        battle.copy_count += 1

        if player is None or battle.copy_count:
            return battle

        # 相手の選出を観測値に置き換える
        name = battle.pokemon[not player].name
        battle.selected[not player] = deepcopy(battle.observed[not player])
        battle.pokemon[not player] = Pokemon.find(battle.selected[not player], name=name)
        
        # 相手ポケモンの情報を補完
        for p in battle.selected[not player]:
            battle.complement_pokemon(p)

        # 相手が後手かつ未行動なら、相手が選択した技を適当な技に置き換える
        if not battle.standby[player] and battle.standby[not player]:
            battle.move[not player] = battle.complement_move(not player)

        # 相手の場のポケモンが瀕死なら、交代コマンドを補完する
        if battle.pokemon[not player].hp == 0:
            battle.reserved_change_commands[not player].append(
                battle.complement_change_command(not player)
            )
            print(f'コマンドを補完 {battle.reserved_change_commands[not player]}')

        return battle

    def estimate_status(self, player: int, name: str, status_index: int) -> bool:
        """ダメージ履歴からポケモンのステータスと補正アイテムを推定し、観測値に上書きする。

        Parameters
        ----------
        player: int

        name: str
        
        status_index: int
            1, 2, 3, 4
            A, B, C, D
        
        Returns
        ----------
        ダメージ履歴に矛盾しないステータスとアイテムが見つかったらTrueを返す。
        """
        match status_index:
            case 1 | 3:
                return self.estimate_attack(player, name, status_index)
            case 2 | 4:
                return self.estimate_defence(player, name, status_index)
            case _:
                warnings.warn(f'status_index is not in [1,2,3,4]')
                return False

    def estimate_attack(self, player: int, name: str, status_index: int, recursive: bool=True) -> bool:
        """ダメージ履歴からポケモンのA/C実数値と補正アイテムを推定し、観測値に上書きする。

        Parameters
        ----------
        player: int

        name: str
        
        status_index: int
            1: A
            3: C
        
        recursive: bool
            再帰的に呼び出す場合はFalseを指定する。
                         
        Returns
        ----------
        ダメージ履歴に矛盾しないステータスとアイテムが見つかったらTrueを返す。
        """

        p2 = Pokemon.find(self.observed[player], name=name)
        battle = Battle()
        cls = 'phy' if status_index == 1 else 'spe'
        signs = []

        # ダメージ履歴を参照する
        for dmg in self.damage_history:

            # 不適切な条件
            if dmg.attack_player != player or dmg.pokemon[player]['_Pokemon__name'] != name or \
                Pokemon.all_moves[dmg.move]['class'] != cls or \
                dmg.move in ['イカサマ','ボディプレス']:
                continue
            
            # ダメージが発生した状況を再現する
            for pl in range(2):
                p = dmg.pokemon[pl]
                battle.pokemon[pl] = Pokemon(p['_Pokemon__name'], use_template=False)
                battle.pokemon[pl].__dict__ |= p
            battle.stellar[player] = dmg.stellar
            battle.condition = dmg.condition

            # 相手の情報は観測値でマスクする
            battle.pokemon[player].ability = p2.ability
            battle.pokemon[player].nature = p2.nature
            battle.pokemon[player].effort = p2.effort.copy()
            battle.pokemon[player].item = p2.item

            # 観測値から想定されるダメージを計算する
            oneshot_damages = battle.oneshot_damages(player, dmg.move, critical=dmg.critical)

            # 観測したダメージを想定値と比較し、ステータスを過大(過少)評価していれば-1(+1)を記録
            signs.append(0)
            if dmg.damage < oneshot_damages[0]:
                signs[-1] = -1
            elif dmg.damage > oneshot_damages[-1]:
                signs[-1] = +1

        # 観測値と想定値に矛盾がなければ終了する
        if not any(signs):
            return True

        if not recursive:
            return False

        # 探索する性格
        nn = p2.nature if Pokemon.nature_corrections[p2.nature][status_index] == 1 else 'まじめ'
        nu = 'いじっぱり' if cls == 'phy' else 'ひかえめ'
        nd = 'ひかえめ' if cls == 'phy' else 'いじっぱり'
        
        # 探索する条件 (低火力順)
        # -0
        # 0
        # 252
        # +252
        # こだわり252
        # こだわり+252

        natures = [nd, nn, nn, nu]
        efforts = [0, 0, 252, 252]
        items = [p2.item]*4

        # アイテムが観測されていない場合は探索条件を追加する
        if not (item_observed := bool(p2.item or p2.lost_item)):
            natures += [nn, nu]
            efforts += [252, 252]
            items += ['こだわりハチマキ' if cls == 'phy' else 'こだわりメガネ']*2
        
        # ダメージが想定より低い場合は探索順を逆にする
        if -1 in signs:
            natures = list(reversed(natures))
            efforts = list(reversed(efforts))
            items = list(reversed(items))

        # 観測値のA/C指数
        eff_status = p2.status[status_index]
        match p2.item:
            case 'こだわりハチマキ':
                if cls == 'phy':
                    eff_status *= Pokemon.item_correction[p2.item]
            case 'こだわりメガネ':
                if cls == 'spe':
                    eff_status *= Pokemon.item_correction[p2.item]
        
        # 現在のA/C指数に最も近い探索条件を見つける
        i = 0
        for i in range(len(natures)):
            effort = [0]*6
            effort[status_index] = efforts[i]
            status = Pokemon.calculate_status(p2.name, natures[i], effort)
            st = status[status_index]

            match items[i]:
                case 'こだわりハチマキ':
                    if cls == 'phy':
                        st *= Pokemon.item_correction[items[i]]
                case 'こだわりメガネ':
                    if cls == 'spe':
                        st *= Pokemon.item_correction[items[i]]

            if +1 in signs:
                if eff_status <= st:
                    break
            else: 
                if eff_status >= st:
                    break

        # 探索範囲を現在のA/C指数以上(過大評価していたら以下)の条件に限定する
        natures = natures[i:]
        efforts = efforts[i:]
        items = items[i:]

        # 上書きする前の観測値
        org_nature = p2.nature
        org_effort = p2.effort.copy()
        org_item = p2.item

        # 探索する
        for i, (nature, effort, item) in enumerate(zip(natures, efforts, items)):
            p2.nature = nature
            p2.set_effort(status_index, effort)
            p2.item = item

            if self.estimate_attack(player, name, status_index, recursive=False):
                return True

        # 観測結果に一致する条件がなければ、観測値を元に戻して終了する
        p2.nature = org_nature
        p2.effort = org_effort
        p2.item = org_item
        return False

    def estimate_defence(self, player: int, name: str, status_index: int, recursive: bool=True) -> bool:
        """ダメージ履歴からポケモンのH,B/D実数値と補正アイテムを推定し、観測値に上書きする。

        Parameters
        ----------
        player: int

        name: str
        
        status_index: int
            2: B
            4: D
        
        recursive: bool
            再帰的に呼び出す場合はFalseを指定する。
                         
        Returns
        ----------
        ダメージ履歴に矛盾しないステータスとアイテムが見つかったらTrueを返す。
        """

        p2 = Pokemon.find(self.observed[player], name=name)
        battle = Battle()
        cls = 'phy' if status_index == 2 else 'spe'
        signs = []

        # ダメージ履歴を参照する
        for dmg in self.damage_history:

            # 不適切な条件
            if dmg.attack_player != player or dmg.pokemon[player]['_Pokemon__name'] != name or \
                Pokemon.all_moves[dmg.move]['class'] != cls or \
                dmg.move in Pokemon.move_category['physical']:
                continue

            # ダメージが発生した状況を再現する
            for pl in range(2):
                p = dmg.pokemon[pl]
                battle.pokemon[pl] = Pokemon(p['_Pokemon__name'], use_template=False)
                battle.pokemon[pl].__dict__ |= p
            battle.stellar[player] = dmg.stellar
            battle.condition = dmg.condition

            # 相手の型は推定値でマスクする
            battle.pokemon[player].ability = p2.ability
            battle.pokemon[player].nature = p2.nature
            battle.pokemon[player].effort = p2.effort.copy()
            battle.pokemon[player].item = p2.item

            # 観測されたダメージ割合と想定しているダメージ割合の大小関係を記録する
            oneshot_damages = battle.oneshot_damages(not player, dmg.move, critical=dmg.critical)
            damage_ratios = [d/battle.pokemon[player].status[0] for d in oneshot_damages]
            
            # ステータスを過大(過少)評価していれば-1(+1)を記録
            signs.append(0)
            if dmg.damage_ratio < damage_ratios[0]:
                signs[-1] = +1
            elif dmg.damage_ratio > damage_ratios[-1]:
                signs[-1] = -1

        # 観測値と想定値に矛盾がなければ終了する
        if not any(signs):
            return True

        if not recursive:
            return False

        # 探索する性格
        nn = p2.nature if Pokemon.nature_corrections[p2.nature][status_index] == 1 else 'まじめ'
        nu = 'のんき' if cls == 'phy' else 'なまいき'
        if Pokemon.nature_corrections[p2.nature][1] == 0.9:
            nu = 'ずぶとい' if cls == 'phy' else 'おだやか'
        elif Pokemon.nature_corrections[p2.nature][3] == 0.9:
            nu = 'わんぱく' if cls == 'phy' else 'しんちょう'
        
        # 探索する条件 (低耐久順)
        # 0
        # H252
        # B/D252
        # HB/D252
        # HB/D+252
        # H252 とつげきチョッキ
        # HD252 とつげきチョッキ

        natures = [nn, nn, nn, nn, nu]
        efforts_H = [0, 252, 0, 252, 252]
        efforts = [0, 0, 252, 252, 252]
        items = [p2.item]*5

        # アイテムが観測されていなければ、とつげきチョッキの可能性も考慮する。
        if not (item_observed := bool(p2.item or p2.lost_item)) and cls == 'spe':
            natures += [nn, nn]
            efforts_H += [252, 252]
            efforts += [0, 252]
            items += ['とつげきチョッキ']*2
        
        # ダメージが想定より低い場合は探索順を逆にする
        if -1 in signs:
            natures = list(reversed(natures))
            efforts_H = list(reversed(efforts_H))
            efforts = list(reversed(efforts))
            items = list(reversed(items))

        # 観測値のB/D指数
        eff_status = p2.status[0] * p2.status[status_index]
        if p2.item == 'とつげきチョッキ' and cls == 'spe':
            eff_status *= 1.5

        # 現在のB/D指数に最も近い探索条件を見つける
        i = 0
        for i in range(len(natures)):
            effort = [efforts_H[i]] + [0]*5
            effort[status_index] = efforts[i]
            status = Pokemon.calculate_status(p2.name, natures[i], effort)
            st = status[0]*status[status_index]*(1+0.5*(items[i] == 'とつげきチョッキ'))
            if +1 in signs:
                if eff_status <= st:
                    break
            else: 
                if eff_status >= st:
                    break
        
        # 探索範囲を現在のB/D指数以上(過大評価していたら以下)の条件に限定する
        natures = natures[i:]
        efforts_H = efforts_H[i:]
        efforts = efforts[i:]
        items = items[i:]

        # 上書きする前の観測値
        org_nature = p2.nature
        org_effort = p2.effort.copy()
        org_item = p2.item

        # 探索する
        for i in range(len(natures)):
            p2.nature = natures[i]
            p2.set_effort(0, efforts_H[i])
            p2.set_effort(status_index, efforts[i])
            p2.item = items[i]

            if self.estimate_defence(player, name, status_index, recursive=False):
                return True

        # 観測結果に一致する条件がなければ、観測値を元に戻して終了する
        p2.nature = org_nature
        p2.effort = org_effort
        p2.item = org_item
        return False

    def proceed(self, commands: list[int]=[None]*2, change_commands: list[int]=[None]*2) -> None:
        """対戦シミュレーション
        
        Parameters
        ----------
        commands: list[int]
            ターン開始時に入力するコマンド
            Noneを指定した場合はself.battle_command()により決定される

        change_commands: list[int]
            任意交代時に入力するコマンド
            Noneを指定した場合はself.change_command()により決定される
        """
        if not any(self.breakpoint):
            self.reset_sim_parameters()
            self.turn += 1

        # 0ターン目は先頭のポケモンを場に出してターンを終了する
        if self.turn == 0:
            # 試合開始直前の乱数シードとポケモンをログに記録
            self._dump['seed'] = self.seed
            for player in range(2):
                self._dump[str(player)] = [deepcopy(vars(p)) for p in self.selected[player]]
            
            if not any(self.breakpoint):
                for player in range(2):
                    self.change_pokemon(player, idx=0, landing=False)

                for player in self.speed_order:
                    self.land(player)

                # だっしゅつパック判定 (0ターン目)
                players = [pl for pl in self.speed_order if self.pokemon[pl].item == 'だっしゅつパック' and \
                    self.pokemon[pl].rank_dropped and self.changeable_indexes(pl)]
                if players:
                    self.breakpoint[players[0]] = 'ejectpack_turn0'
                    self.consume_item(players[0])
                    for pl in players:
                        self.pokemon[pl].rank_dropped = False

            # だっしゅつパックによる交代
            if (s := 'ejectpack_turn0') in self.breakpoint:
                player = self.breakpoint.index(s)
                self.change_pokemon(player, command=change_commands[player])
                change_commands[player] = None # コマンド破棄
            
            # このターンに入力されたコマンドを記録
            self.record_command()

            return

        if not any(self.breakpoint):
            for player in range(2):
                # コマンドが指定されていなければ方策関数を呼び出す
                if commands[player] is None:
                    self.command[player] = self.battle_command(player)
                else:
                    self.command[player] = commands[player]

                self.log[player].append(self.pokemon[player].name)
                self.log[player].append(f'HP {self.pokemon[player].hp}/{self.pokemon[player].status[0]}')
                self.log[player].append(f'コマンド {self.command[player]}')

            # 素早さ実効値を更新
            self.update_speed_order()

            # 優先度を考慮して行動順を決定
            move_speeds = []

            for player,p in enumerate(self.pokemon):
                # 素早さ (1e-1)
                self.speed[player] -= 0.1*self.speed_order.index(player)

                # 行動しない
                if self.command[player] == Battle.SKIP:
                    self.speed[player] += 1000
                    continue

                # 交代 (1e+2)
                if self.command[player] in range(20,30):
                    self.speed[player] += 100
                    continue

                # 技の修正
                if self.command[player] in range(20):
                    self.move[player] = p.moves[self.command[player]%10]
                elif self.command[player] == Battle.STRUGGLE:
                    self.move[player] = 'わるあがき'
                elif self.command[player] == Battle.NO_COMMAND:
                    if p.last_used_move in Pokemon.move_category['immovable']:
                        self.move[player] = None
                        self.pokemon[player].inaccessible = 0
                    else:
                        self.move[player] = p.last_used_move

                if not self.move[player]:
                    continue

                # 技の行動速度 (1e+1~1e0)
                move_speeds.append(self.move_speed(player, self.move[player]))
                self.speed[player] += move_speeds[-1]
                
            self.action_order = [int(self.speed[0] < self.speed[1]), int(self.speed[0] > self.speed[1])]

            for player in range(2):
                self.log[player].append('先手' if player == self.action_order[0] else '後手')

                # 行動順から相手のSのとりうる範囲を計算する
                # 相手のS補正量
                p = Pokemon.find(self.observed[not player], display_name=self.pokemon[not player].display_name)
                r_speed = self.eff_speed(not player) / p.status[5]
                
                # 相手のSの上下限 = 自分のS / 相手のS補正値
                speed = self.pokemon[player].status[5] / r_speed
                
                # 相手が先手ならSの最小値を、後手なら最大値を更新する
                if player == self.action_order[0]:
                    p.speed_range[0] = max(p.speed_range[0], speed)
                else:
                    p.speed_range[1] = min(p.speed_range[1], speed)

        # 交代
        for player in range(2):
            if not any(self.breakpoint) and self.command[player] in range(20,30):
                self.change_pokemon(player, command=self.command[player])

                # だっしゅつパック判定 (交代後)
                players = [pl for pl in self.speed_order if self.pokemon[pl].item == 'だっしゅつパック' and \
                    self.pokemon[pl].rank_dropped and self.changeable_indexes(pl)]
                if players:
                    self.breakpoint[players[0]] = f'ejectpack_change_{player}'
                    self.consume_item(players[0])
                    for pl in players:
                        self.pokemon[pl].rank_dropped = False

            # だっしゅつパックによる交代
            if (s := f'ejectpack_change_{player}') in self.breakpoint:
                pl = self.breakpoint.index(s)
                self.change_pokemon(pl, command=change_commands[pl])
                change_commands[pl] = None # コマンド破棄
            
        if not any(self.breakpoint):
            # テラスタル
            for player in range(2):
                if self.command[player] in range(10,20) and self.pokemon[player].use_terastal():
                    self.log[player].append(f'テラスタル {self.pokemon[player].Ttype}')

                    if 'オーガポン' in self.pokemon[player].name:
                        if self.pokemon[not player].ability == 'かがくへんかガス' and self.pokemon[player].item != 'とくせいガード':
                            self.pokemon[player].ability = ''
                            self.log[player].append('かがくへんかガス 特性無効')
                        else:
                            self.release_ability(player)

                    if 'テラパゴス' in self.pokemon[player].name:
                        if self.pokemon[not player].ability == 'かがくへんかガス' and self.pokemon[player].item != 'とくせいガード':
                            self.pokemon[player].ability = ''
                            self.log[player].append('かがくへんかガス 特性無効')
                        else:
                            removed = self.set_weather(player, '')
                            removed |= self.set_field(player, '')
                            if removed:
                                self.log[player].insert(-1, self.pokemon[player].ability)

                    # テラスタルの観測
                    p_obs = Pokemon.find(self.observed[player], display_name=self.pokemon[player].display_name)
                    p_obs.Ttype = self.pokemon[player].Ttype
                    p_obs.use_terastal()

            ### ターン処理
            self.protect = '' # まもる系
            self.koraeru = False # こらえる
            self.flinch = False # ひるみ

        # ターン行動
        for player in self.action_order:
            player2 = not player # 防御側
            move = self.move[player]
            move_class = Pokemon.all_moves[move]['class'] if move else None

            if not any(self.breakpoint):
                self.standby[player] = False

                # 行動をスキップする特殊コマンド
                if self.command[player] == Battle.SKIP:
                    self.log[player].append('行動スキップ')
                    continue
                
                # 交代した場合
                if self.has_changed[player]:
                    self.log[player].append('行動不能 交代')
                    continue

                # みちづれ解除
                self.pokemon[player].condition['michizure'] = 0

                # 反動で動けない
                if not move:
                    self.log[player].append('行動不能 反動')
                    self.pokemon[player].last_used_move = ''
                    continue

                # 眠り判定
                if self.pokemon[player].ailment == 'SLP':
                    self.pokemon[player].sleep_count -= (2 if self.pokemon[player].ability == 'はやおき' else 1)
                    if self.pokemon[player].sleep_count <= 0:
                        self.set_ailment(player, '')
                    else:
                        self.log[player].append(f'ねむり 残り{self.pokemon[player].sleep_count}ターン')
                        if move not in ['ねごと','いびき']:
                            self.pokemon[player].last_used_move = ''
                            continue

                # こおり判定
                elif self.pokemon[player].ailment == 'FLZ':
                    if move in Pokemon.move_category['unfreeze'] or self._random.random() < 0.2:
                        self.set_ailment(player, '')
                    else:
                        self.log[player].append('行動不能 こおり')
                        self.pokemon[player].last_used_move = ''
                        continue
                
                # なまけ判定
                if 'なまけ' in (ability := self.pokemon[player].ability):
                    self.pokemon[player].ability = ability[:-1] if ability[-1] == '+' else ability + '+'
                    if self.pokemon[player].ability[-1] != '+':
                        self.log[player].append('行動不能 なまけ')
                        self.pokemon[player].last_used_move = ''
                        continue

                # ひるみ判定
                if self.flinch:
                    self.log[player].append('行動不能 ひるみ')
                    if self.pokemon[player].ability == 'ふくつのこころ' and self.add_rank(player, 5, +1):
                        self.log[player].insert(-1, self.pokemon[player].ability)
                    self.pokemon[player].last_used_move = ''
                    continue

                # 選択できない技
                if (s := self.unusable_reason(player, move)):
                    self.log[player].append(f'{move} {s} 不発')
                    self.pokemon[player].last_used_move = ''
                    continue

                # こんらん判定
                if self.pokemon[player].condition['confusion']:
                    self.pokemon[player].condition['confusion'] -= 1
                    self.log[player].append(f"こんらん 残り{self.pokemon[player].condition['confusion']}ターン")
                    if self._random.random() < 0.25:
                        oneshot_damage = self.oneshot_damages(player, 'わるあがき', self_harm=True)
                        self.add_hp(player, -self.choose_damage(player, oneshot_damage), move='わるあがき')
                        self.log[player].insert(-1, 'こんらん自傷')
                        self.pokemon[player].last_used_move = ''
                        continue
                    
                # しびれ判定
                if self.pokemon[player].ailment == 'PAR':
                    if self._random.random() < 0.25:
                        self.log[player].append('行動不能 しびれ')
                        self.pokemon[player].last_used_move = ''
                        continue

                # メロメロ判定
                if self.pokemon[player].condition['meromero'] and self._random.random() < 0.5:
                    self.log[player].append('行動不能 メロメロ')
                    self.pokemon[player].last_used_move = ''
                    continue

                # PP消費
                self.pokemon[player].last_pp_move = move if move != 'わるあがき' else ''

                if self.pokemon[player].inaccessible == 0 and (ind := self.pokemon[player].last_pp_move_index()) is not None:
                    v = 2 if self.pokemon[not player].ability == 'プレッシャー' else 1
                    self.pokemon[player].pp[ind] = max(0, self.pokemon[player].pp[ind] - v)
                    self.log[player].append(f'{move} PP {self.pokemon[player].pp[ind]}')

                    # 技の観測
                    p_obs = Pokemon.find(self.observed[player], name=self.pokemon[player].name)
                    p_obs.add_move(move)
                    p_obs.pp[p_obs.moves.index(move)] = self.pokemon[player].pp[ind] # PPは既知とする

                # ねごとによる技の変更
                if move == 'ねごと':
                    unselected_moves = [''] + Pokemon.move_category['non_negoto'] + Pokemon.move_category['charge']
                    candidates = [move for move in self.pokemon[player].moves if move not in unselected_moves]

                    if self.pokemon[player].ailment == 'SLP' and candidates:
                        move = self._random.choice(candidates)
                        move_class = Pokemon.all_moves[move]['class']
                        self.log[player].append(f'ねごと -> {move}')

                        # 技の観測
                        p_obs = Pokemon.find(self.observed[player], name=self.pokemon[player].name)
                        p_obs.add_move(move)
                    else:
                        self.was_valid[player] = False
        
                # まもる系の連発
                if move in Pokemon.move_category['protect'] and \
                    self.pokemon[player].last_used_move in Pokemon.move_category['protect']:
                    self.was_valid[player] = False

                # 場に出たターンしか使えない技
                if move in Pokemon.move_category['first_act'] and self.pokemon[player].acted_turn:
                    self.was_valid[player] = False

                # 発動する技の確定
                self.pokemon[player].last_used_move = move if self.was_valid[player] else ''

                # こだわりによる技の固定
                if self.pokemon[player].item[:4] == 'こだわり' or self.pokemon[player].ability == 'ごりむちゅう' and \
                    not self.pokemon[player].fixed_move:
                        self.pokemon[player].fixed_move = self.pokemon[player].last_pp_move

                # わざの発動制限
                match move:
                    case 'アイアンローラー':
                        self.was_valid[player] = bool(self.field())
                    case 'いびき':
                        self.was_valid[player] = self.pokemon[player].ailment == 'SLP'
                    case 'じんらい' | 'ふいうち':
                        self.was_valid[player] = player == self.action_order[0] and \
                            self.move[player2] and Pokemon.all_moves[self.move[player2]]['class'] in ['phy','spe']
                    case 'なげつける':
                        self.was_valid[player] = bool(self.pokemon[player].item) and self.pokemon[player].item_removable()
                    case 'はやてがえし':
                        self.was_valid[player] = player == self.action_order[0] and self.speed[player2] > 5
                    case 'ポルターガイスト':
                        self.was_valid[player] = bool(self.pokemon[player2].item)

                # 特性による発動制限
                if self.pokemon[player2].ability in ['じょおうのいげん','テイルアーマー','ビビッドボディ'] and \
                    self.speed[player] > 5:
                    self.was_valid[player] = False
                    self.log[player].append(self.pokemon[player2].ability)
                    
                    # 特性の観測
                    Pokemon.find(self.observed[player2], name=self.pokemon[player2].name).ability = \
                        self.pokemon[player2].ability
                
                if 'しめりけ' in (abilities := [p.ability for p in self.pokemon]) and \
                    move in ['じばく','だいばくはつ','ビックリヘッド','ミストバースト']:
                    self.was_valid[player] = False
                    self.log[player].append('しめりけ')

                    # 特性の観測
                    if abilities.index('しめりけ') == player2:
                        Pokemon.find(self.observed[player2], name=self.pokemon[player2].name).ability = \
                            self.pokemon[player2].ability

                # へんげんじざい判定
                if self.pokemon[player].ability in ['へんげんじざい','リベロ'] and self.was_valid[player] and \
                    not self.pokemon[player].terastal and move != 'わるあがき' and \
                    self.pokemon[player].types == self.pokemon[player].org_types and \
                    self.pokemon[player].types != [t := Pokemon.all_moves[move]['type']]:
                    self.pokemon[player].lost_types += self.pokemon[player].types
                    self.pokemon[player].added_types += [t]
                    self.log[player].append(f'{self.pokemon[player].ability} {t}タイプ')

                    # 特性の観測
                    Pokemon.find(self.observed[player], name=self.pokemon[player].name).ability = \
                        self.pokemon[player].ability

                # ため技
                if move in Pokemon.move_category['charge'] + Pokemon.move_category['hide']:
                    self.pokemon[player].inaccessible = not self.pokemon[player].inaccessible

                    if self.pokemon[player].inaccessible:
                        # 発動前処理
                        if move in Pokemon.move_category['hide']:
                            self.pokemon[player].hide_move = move
                        else:
                            match move:
                                case 'メテオビーム' | 'エレクトロビーム':
                                    self.add_rank(player, 3, +1)
                                case 'ロケットずつき':
                                    self.add_rank(player, 2, +1)
                        
                        # 溜め解除
                        if ('ソーラー' in move and self.weather(player) == 'sunny') or \
                            (move == 'エレクトロビーム' and self.weather(player) == 'rainy'):
                            self.pokemon[player].inaccessible = 0
                            self.log[player].append(f'{move} 溜め省略')
                        elif self.pokemon[player].item == 'パワフルハーブ':
                            self.consume_item(player)
                        else:
                            self.log[player].append('行動不能 溜め')
                            continue
                    
                self.pokemon[player].hide_move = ''
                        
                # 強制反動技
                if move in Pokemon.move_value['force_rebound'] and self.was_valid[player] and \
                    self.add_hp(player, -round_half_up(self.pokemon[player].status[0] * Pokemon.move_value['force_rebound'][move])):
                    self.log[player].insert(-1, '反動')
                    if self.pokemon[player].hp == 0 and self.winner(record=True) is not None: # 勝敗判定
                        return

                # サイコフィールドによる先制技無効
                if self.condition['psycofield'] and self.speed[player] > 5:
                    self.was_valid[player] = False
                    self.log[player].append('行動不能 サイコフィールド')

                # あくタイプによるいたずらごころ無効
                if self.pokemon[player].ability == 'いたずらごころ' and 'あく' in self.pokemon[player2].types and \
                    self.pokemon[player].last_pp_move and self.pokemon[player].last_used_move and \
                    (Pokemon.all_moves[self.pokemon[player].last_pp_move]['class'][-3] == '1' or \
                    ('sta' in Pokemon.all_moves[self.pokemon[player].last_pp_move]['class'] and \
                     Pokemon.all_moves[self.pokemon[player].last_used_move]['class'] in ['phy','spe'])):
                    self.was_valid[player] = False
                    self.log[player].append('いたずらごころ無効')

                    # 特性の観測
                    Pokemon.find(self.observed[player], name=self.pokemon[player].name).ability = \
                        self.pokemon[player].ability

                # わざが無効なら中断
                if not self.was_valid[player]:
                    self.log[player].append(f'{move} 失敗')
                    continue

                # まもる判定
                if self.protect and move not in Pokemon.move_category['unprotect'] and \
                    not (self.pokemon[player].ability == 'ふかしのこぶし' and self.pokemon[player].contacts(move)):

                    self.was_valid[player2] = move_class in ['phy','spe']
                    if self.protect != 'かえんのまもり':
                        self.was_valid[player2] |= move_class[-1] == '1'

                    if self.was_valid[player2]:
                        # 追加効果
                        if self.pokemon[player].contacts(move):
                            match self.protect:
                                case 'かえんのまもり':
                                    if self.set_ailment(player, 'BRN'):
                                        self.log[player].insert(-1, '追加効果')
                                case 'トーチカ':
                                    if self.set_ailment(player, 'PSN'):
                                        self.log[player].insert(-1, '追加効果')
                                case 'ニードルガード':
                                    if self.add_hp(player, -int(self.pokemon[player].status[0]/8)):
                                        self.log[player].insert(-1, '追加効果')
                                case 'スレッドトラップ':
                                    self.add_rank(player, 5, -1, by_enemy=True)

                        # 反動ダメージ             
                        if move in Pokemon.move_value['mis_rebound'] and \
                            self.add_hp(player, -int(self.pokemon[player].status[0] * Pokemon.move_value['mis_rebound'][move])):
                            self.log[player].insert(-1, '反動')

                        self.pokemon[player].inaccessible = 0
                        self.log[player].append(f'{self.protect}')
                        continue
                
                # 技の発動処理
                n_hit = self.num_hits(player, move)
                if n_hit > 1:
                    self.log[player].append(f'{n_hit}発')
                hits = True

                for i in range(n_hit):
                    # 命中判定
                    if i == 0 or Pokemon.combo_hit[move][1] in [3,10]:
                        hits = self._random.random() < self.hit_probability(player, move)
                        
                    if not hits:
                        if i == 0:
                            self.log[player].append('はずれ')
                            self.pokemon[player].inaccessible = 0
                            self.was_valid[player] = False
                        else:
                            self.log[player].append(f'{i}ヒット')

                        if move in Pokemon.move_value['mis_rebound'] and \
                            self.add_hp(player, -int(self.pokemon[player].status[0] * Pokemon.move_value['mis_rebound'][move])):
                            self.log[player].insert(-1, '反動')

                        if i == 0 and self.pokemon[player].item == 'からぶりほけん' and \
                            move not in Pokemon.move_category['one_ko'] and self.pokemon[player].rank[5] < 6:
                                self.consume_item(player)
                                self.was_valid[player] = True
                        
                        break
                    
                    # 攻撃技の処理
                    if Pokemon.all_moves[move]['class'] in ['phy', 'spe']:                    
                        # 急所判定
                        critical = self._random.random() < self.critical_probability(player, move)
                        if critical:
                            self.log[player].append('急所')

                        # ダメージ計算
                        if Pokemon.all_moves[move]['power'] > 0:
                            pf = i+1 if move == 'トリプルアクセル' else 1
                            oneshot_damages = self.oneshot_damages(player, move, critical=critical, power_factor=pf)
                            self.damage[player] = self.choose_damage(player, oneshot_damages) if oneshot_damages else 0
                            
                            # ダメージの観測
                            if self.damage[player]:
                                self.damage_history.append(Damage())
                                self.damage_history[-1].turn = self.turn
                                self.damage_history[-1].attack_player = player
                                self.damage_history[-1].index = [self.current_index(pl) for pl in range(2)]
                                self.damage_history[-1].pokemon = [deepcopy(vars(p)) for p in self.pokemon]
                                self.damage_history[-1].move = move
                                self.damage_history[-1].damage = self.damage[player]
                                self.damage_history[-1].damage_ratio = self.damage[player]/self.pokemon[not player].status[0]
                                self.damage_history[-1].critical = critical
                                self.damage_history[-1].stellar = self.stellar[player].copy()
                                self.damage_history[-1].condition = self.condition.copy()
                                #print(vars(self.damage_history[-1]))

                        # ダメージ計算適用外
                        elif self.defence_type_correction(player, move) and self.damage_correction(player, move):
                            match move:
                                case 'ぜったいれいど' | 'じわれ' | 'つのドリル' | 'ハサミギロチン':
                                    if self.ability(player2, move) != 'がんじょう' or \
                                        not (move == 'ぜったいれいど' and 'こおり' in self.pokemon[player2].types):
                                        self.damage[player] = self.pokemon[player2].hp
                                case 'いかりのまえば' | 'カタストロフィ':
                                    self.damage[player] = int(self.pokemon[player2].hp/2)
                                case 'カウンター' | 'ミラーコート':
                                    s = 'phy' if move == 'カウンター' else 'spe'
                                    if self.pokemon[player2].last_used_move and Pokemon.all_moves[self.pokemon[player2].last_used_move]['class'] == s:
                                        self.damage[player] = int(self.damage[player2]*2)
                                case 'ほうふく' | 'メタルバースト':
                                    self.damage[player] = int(self.damage[player2]*1.5)
                                case 'ちきゅうなげ' | 'ナイトヘッド':
                                    self.damage[player] = self.pokemon[player].level
                                case 'いのちがけ':
                                    self.damage[player] = self.pokemon[player].hp
                                    self.pokemon[player].hp = 0
                                    if self.winner(record=True) is None: # 勝敗判定
                                        return
                                    else:
                                        self.log[player].append(f'いのちがけ {-self.damage[player]}')
                                case 'がむしゃら':
                                    self.damage[player] = max(0, self.pokemon[player2].hp - self.pokemon[player].hp)

                        if self.damage[player] == 0:
                            self.pokemon[player].inaccessible = 0
                            self.was_valid[player] = False
                        else:
                            # 壁破壊
                            if self.damage[player] and move in Pokemon.move_category['wall_break']:
                                if self.condition['reflector'][player2] + self.condition['lightwall'][player2]:
                                    self.condition['reflector'][player2] = self.condition['lightwall'][player2] = 0
                                    self.log[player].append('かべ破壊')

                            # ダメージ計算中に使用したアイテムの消費
                            for j in range(2):
                                if self.pokemon[j].item in self.damage_log[j]:
                                    self.damage_log[j].remove(f'{self.pokemon[j].item}')
                                    self.consume_item(j)

                            # ダメージ付与
                            substituted = self.pokemon[player2].sub_hp and move not in Pokemon.move_category['sound'] and self.pokemon[player].ability != 'すりぬけ'
                            if substituted:
                                # ダメージ上限 = みがわり残りHP
                                self.damage[player] = min(self.pokemon[player2].sub_hp, self.damage[player])
                                self.pokemon[player2].sub_hp -= self.damage[player]
                                if self.pokemon[player2].sub_hp:
                                    self.log[player2].append(f'みがわりHP {self.pokemon[player2].sub_hp}')
                                else:
                                    self.log[player2].append(f'みがわり消滅')
                            elif self.ability(player2, move) == 'ばけのかわ':
                                self.damage[player] = 0
                                self.add_hp(player2, -int(self.pokemon[player2].status[0]/8))
                                self.log[player2].insert(-1, self.pokemon[player2].ability)
                                self.pokemon[player2].ability = 'ばけのかわ+'
                            else:
                                # ダメージ上限 = 残りHP
                                self.damage[player] = min(self.pokemon[player2].hp, self.damage[player])

                                # ダメージ修正
                                if self.damage[player] == self.pokemon[player2].hp:
                                    # こらえる
                                    if self.koraeru:
                                        self.damage[player] -= 1
                                        self.was_valid[player2] = True
                                    # きあいのハチマキ
                                    elif self.pokemon[player2].item == 'きあいのハチマキ' and self._random.random() < 0.1:
                                        self.damage[player] -= 1
                                        self.log[player].append(f'{self.pokemon[player2].item}発動')
                                    # がんじょう・きあいのタスキ
                                    elif self.pokemon[player2].hp == self.pokemon[player2].status[0]:
                                        if self.ability(player2, move) == 'がんじょう':
                                            self.damage[player] -= 1
                                            self.log[player].append(self.pokemon[player2].ability)

                                            # 特性の観測
                                            Pokemon.find(self.observed[player2], name=self.pokemon[player2].name).ability = \
                                                self.pokemon[player2].ability

                                        elif self.pokemon[player2].item == 'きあいのタスキ':
                                            self.damage[player] -= 1
                                            self.consume_item(player2)

                                # HP更新
                                self.add_hp(player2, -self.damage[player], move=move)
                                self.log[player].append(f'ダメージ {self.damage[player]}')
                                self.log[player].append(f'相手HP {self.pokemon[player2].hp}')

                                # 被弾回数を記録
                                self.pokemon[player2].n_attacked += 1

                                if self.pokemon[player2].hp == 0 and self.winner(record=True) is not None: # 勝敗判定
                                    return

                            # 追加効果 (ランク変化・状態異常・ひるみ)
                            if move in Pokemon.move_effect:
                                effect = Pokemon.move_effect[move]
                                pl = (effect['object'] + player) % 2
                                p = self.pokemon[pl]
                                r_prob = 2 if self.pokemon[player].ability == 'てんのめぐみ' else 1

                                if (pl == player or (self.can_move_affects(player, move) and not substituted)) and \
                                    self._random.random() < effect['prob'] * r_prob:
                                    if any(effect['rank']):
                                        if self.add_rank(pl, 0, 0, rank_list=effect['rank']):
                                            self.log[player].insert(-1, '追加効果')
                                    
                                    if any(effect['ailment']):
                                        candidates = [s for (j,s) in enumerate(Pokemon.ailments) if effect['ailment'][j]]
                                        s = self._random.choice(candidates)
                                        if self.set_ailment(pl, s, badpoison=(effect['ailment'][0] == 2)):
                                            self.log[player].insert(-1, '追加効果')

                                    if effect['confusion']:
                                        if self.set_condition(pl, 'confusion'):
                                            self.log[player].append('追加効果 こんらん')

                                if effect['flinch'] and self.pokemon[player2].ability != 'せいしんりょく':
                                    self.flinch = self._random.random() < effect['flinch'] * r_prob
                                    if self.flinch:
                                        self.log[player].append('追加効果 ひるみ')

                            # 追加効果 (その他)
                            if not substituted and self.can_move_affects(player, move):
                                # わざ以外のひるみ判定
                                if self.pokemon[player2].ability != 'せいしんりょく' and not self.flinch and \
                                    (move not in Pokemon.move_effect or (move in Pokemon.move_effect and Pokemon.move_effect[move]['flinch'] == 0)):
                                    if self.pokemon[player].ability == 'あくしゅう':
                                        self.flinch = self._random.random() < 0.1
                                    elif self.pokemon[player].item in ['おうじゃのしるし','するどいキバ']:
                                        self.flinch = self._random.random() < 0.1*(2 if self.pokemon[player].ability == 'てんのめぐみ' else 1)

                                    if self.flinch:
                                        self.log[player].append('追加効果 ひるみ')

                                match move:
                                    case 'アンカーショット' | 'かげぬい':
                                        if not self.pokemon[player2].condition['change_block']:
                                            self.pokemon[player2].condition['change_block'] = 1
                                            self.log[player].append('追加効果 にげられない')
                                    case 'サイコノイズ':
                                        if self.pokemon[player2].condition['healblock'] == 0:
                                            self.pokemon[player2].condition['healblock'] = 2
                                            self.log[player].append('追加効果 かいふくふうじ')
                                    case 'しおづけ':
                                        if not self.pokemon[player2].condition['shiozuke']:
                                            self.pokemon[player2].condition['shiozuke'] = 1
                                            self.log[player].append('追加効果 しおづけ')
                                    case 'じごくづき':
                                        if self.pokemon[player2].condition['jigokuzuki'] == 0:
                                            self.pokemon[player2].condition['jigokuzuki'] = 2
                                            self.log[player].append('追加効果 じごくづき')
                                    case 'なげつける':
                                        match self.pokemon[player].item:
                                            case 'おうじゃのしるし' | 'するどいキバ':
                                                self.flinch = True
                                                self.log[player].append('追加効果 ひるみ')
                                            case 'かえんだま':
                                                if self.set_ailment(player2, 'BRN', move):
                                                    self.log[player].insert(-1, '追加効果')
                                            case 'でんきだま':
                                                if self.set_ailment(player2, 'PAR', move):
                                                    self.log[player].insert(-1, '追加効果')
                                            case 'どくバリ':
                                                if self.set_ailment(player2, 'PSN', move):
                                                    self.log[player].insert(-1, '追加効果')
                                            case 'どくどくだま':
                                                if self.set_ailment(player2, 'PSN', move, badpoison=True):
                                                    self.log[player].insert(-1, '追加効果')

                                    case 'みずあめボム':
                                        if self.pokemon[player2].condition['ame_mamire'] == 0:
                                            self.pokemon[player2].condition['ame_mamire'] = 3
                                            self.log[player].append('追加効果 あめまみれ')

                            # なげつけるによるアイテム消失
                            if move == 'なげつける':
                                self.pokemon[player].item, self.pokemon[player].lost_item = '', self.pokemon[player].item
                                self.log[player].append(f'{self.pokemon[player].lost_item}消失')

                                # アイテムの観測
                                p_obs = Pokemon.find(self.observed[player], name=self.pokemon[player].name)
                                p_obs.item, p_obs.lost_item = self.pokemon[player].item, self.pokemon[player].lost_item

                            # HP吸収
                            if move in Pokemon.move_value['drain'] and self.damage[player] and \
                                self.add_hp(player, self.absorbed_value(player, Pokemon.move_value['drain'][move]*self.damage[player])):
                                self.log[player].insert(-1, 'HP吸収')

                            # みがわりを攻撃した場合は、与えたダメージを0とする
                            if substituted:
                                self.damage[player] = 0

                            if move == 'コアパニッシャー' and not substituted:
                                if player == self.action_order[-1] and self.pokemon[player2].ability not in Pokemon.ability_category['protected']:
                                    self.log[player].append(f'追加効果 {self.pokemon[player2].ability}消失')
                                    self.pokemon[player2].ability = ''

                            if move == 'クリアスモッグ' and not substituted:
                                if any(self.pokemon[player2].rank):
                                    self.log[player].append('追加効果 ランクリセット')
                                    self.pokemon[player2].rank = [0]*8

                            # おんねん判定
                            # くちばしキャノン判定

                            # 攻撃側の特性
                            if not substituted and self.can_move_affects(player, move):
                                observed = False

                                match self.pokemon[player].ability:
                                    case 'どくしゅ':
                                        if self.pokemon[player].contacts(move) and self._random.random() < 0.3 and self.set_ailment(player2, 'PSN'):
                                            self.log[player].insert(-1, self.pokemon[player].ability)
                                            observed = True
                                    case 'どくのくさり':
                                        if self._random.random() < 0.3 and self.set_ailment(player2, 'PSN', badpoison=True):
                                            self.log[player].insert(-1, self.pokemon[player].ability)
                                            observed = True

                                # 特性の観測
                                if observed:
                                    Pokemon.find(self.observed[player], name=self.pokemon[player].name).ability = \
                                        self.pokemon[player].ability

                            # 防御側の特性
                            if not substituted:
                                observed = False

                                match self.pokemon[player2].ability:
                                    case 'いかりのつぼ':
                                        if critical and self.add_rank(player2, 1, +12):
                                            self.log[player2].insert(-1, self.pokemon[player2].ability)
                                            observed = True
                                    case 'うのミサイル':
                                        pass#observed = True
                                    case 'こぼれダネ':
                                        if self.set_field(player2, 'glassfield'):
                                            self.log[player2].insert(-1, self.pokemon[player2].ability)
                                            observed = True
                                    case 'じきゅうりょく':
                                        if self.add_rank(player2, 2, +1):
                                            self.log[player2].insert(-1, self.pokemon[player2].ability)
                                            observed = True
                                    case 'じょうききかん':
                                        if self.move_type(player, move) in ['みず','ほのお'] and self.add_rank(player2, 5, +6):
                                            self.log[player2].insert(-1, self.pokemon[player2].ability)
                                            observed = True
                                    case 'すなはき':
                                        if self.set_weather(player2, 'sandstorm'):
                                            self.log[player2].insert(-1, self.pokemon[player2].ability)
                                            observed = True
                                    case 'せいぎのこころ' | 'ねつこうかん':
                                        t = 'あく' if self.pokemon[player2].ability == 'せいぎのこころ' else 'ほのお'
                                        if self.move_type(player, move) == t and self.add_rank(player2, 1, +1):
                                            self.log[player2].insert(-1, self.pokemon[player2].ability)
                                            observed = True
                                    case 'でんきにかえる':
                                        if not self.pokemon[player2].condition['charge']:
                                            self.pokemon[player2].condition['charge'] = 1
                                            self.log[player2].append(f'{self.pokemon[player2].ability} じゅうでん')
                                            observed = True
                                    case 'のろわれボディ':
                                        if not self.pokemon[player].condition['kanashibari'] and self._random.random() < 0.3:
                                            self.pokemon[player].condition['kanashibari'] = 1
                                            self.log[player2].append(f'{self.pokemon[player2].ability} {self.pokemon[player].last_pp_move} かなしばり')
                                            observed = True
                                    case 'びびり':
                                        if self.move_type(player, move) in ['あく','ゴースト','むし'] and self.add_rank(player2, 5, +1):
                                            self.log[player2].insert(-1, self.pokemon[player2].ability)
                                            observed = True
                                    case 'ふうりょくでんき':
                                        if move in Pokemon.move_category['wind'] and not self.pokemon[player2].condition['charge']:
                                            self.pokemon[player2].condition['charge'] = 1
                                            self.log[player2].append(f'{self.pokemon[player2].ability} じゅうでん')
                                            observed = True
                                    case 'みずがため':
                                        if self.move_type(player, move) == 'みず' and self.add_rank(player2, 2, +2):
                                            self.log[player2].insert(-1, self.pokemon[player2].ability)
                                            observed = True
                                    case 'わたげ':
                                        if self.add_rank(player, 5, -1):
                                            self.log[player2].append(self.pokemon[player2].ability)
                                            observed = True

                                # 物理攻撃時のみ
                                match self.pokemon[player2].ability * (Pokemon.all_moves[move]['class'] == 'phy'):
                                    case 'くだけるよろい':
                                        if self.add_rank(player2, 0, 0, [0,0,-1,0,0,2]):
                                            self.log[player2].insert(-1, self.pokemon[player2].ability)
                                            observed = True
                                    case 'どくげしょう':
                                        if self.condition['dokubishi'][player] < 2:
                                            self.condition['dokubishi'][player] += 1
                                            self.log[player].append(f"どくびし {self.condition['dokubishi'][player]}")
                                            self.log[player2].append(self.pokemon[player2].ability)
                                            observed = True

                                # 接触時のみ
                                match self.pokemon[player2].ability * self.pokemon[player].contacts(move):
                                    case 'さまようたましい':
                                        if not self.pokemon[player].has_protected_ability():
                                            self.pokemon[player].ability, self.pokemon[player2].ability = \
                                                self.pokemon[player2].ability, self.pokemon[player].ability
                                            for pl in range(2):
                                                self.log[pl].append(f'-> {self.pokemon[pl].ability}')
                                            observed = True
                                    case 'さめはだ' | 'てつのトゲ':
                                        if self.add_hp(player, -int(self.pokemon[player].status[0]/8)):
                                            self.log[player2].append(self.pokemon[player2].ability)
                                            observed = True
                                    case 'せいでんき':
                                        if self._random.random() < 0.3 and self.set_ailment(player, 'PAR'):
                                            self.log[player2].append(self.pokemon[player2].ability)
                                            observed = True
                                    case 'どくのトゲ':
                                        if self._random.random() < 0.3 and self.set_ailment(player, 'PSN'):
                                            self.log[player2].append(self.pokemon[player2].ability)
                                            observed = True
                                    case 'とれないにおい' | 'ミイラ':
                                        if not self.pokemon[player].has_protected_ability():
                                            self.pokemon[player].ability = self.pokemon[player2].ability
                                            self.log[player].append(f'-> {self.pokemon[player2].ability}')
                                            observed = True
                                    case 'ぬめぬめ' | 'カーリーヘアー':
                                        if self.add_rank(player, 5, -1, by_enemy=True):
                                            self.log[player2].append(self.pokemon[player2].ability)
                                            observed = True
                                    case 'ほうし':
                                        if self._random.random() < 0.3:
                                            self.set_ailment(player, self._random.choice(['PSN', 'PAR', 'SLP']))
                                            self.log[player2].append(self.pokemon[player2].ability)
                                            observed = True
                                    case 'ほのおのからだ':
                                        if self._random.random() < 0.3 and self.set_ailment(player, 'BRN'):
                                            self.log[player2].append(self.pokemon[player2].ability)
                                            observed = True
                                    case 'ほろびのボディ':
                                        for j in range(2):
                                            if self.pokemon[j].condition['horobi'] == 0:
                                                self.pokemon[j].condition['horobi'] = 4
                                                self.log[j].append(self.pokemon[player2].ability)
                                                observed = True
                                    case 'メロメロボディ':
                                        if self._random.random() < 0.3 and self.set_condition(player, 'meromero'):
                                            self.log[player2].append(self.pokemon[player2].ability)
                                            observed = True
                                    case 'ゆうばく':
                                        if self.pokemon[player2].hp == 0 and self.add_hp(player, -int(self.pokemon[player].status[0]/4)):
                                            self.log[player2].append(self.pokemon[player2].ability)
                                            observed = True

                                # 特性の観測
                                if observed:
                                    Pokemon.find(self.observed[player2], name=self.pokemon[player2].name).ability = \
                                        self.pokemon[player2].ability

                            # やきつくす判定
                            if move == 'やきつくす' and self.pokemon[player2].item and \
                                (self.pokemon[player2].item[-2:] == 'のみ' or 'ジュエル' in self.pokemon[player2].item):
                                self.log[player].append(f'追加効果 {self.pokemon[player2].item}消失')
                                self.pokemon[player2].item, self.pokemon[player2].lost_item = '', self.pokemon[player2].item

                                # アイテムの観測
                                p_obs = Pokemon.find(self.observed[player2], name=self.pokemon[player2].name)
                                p_obs.item, p_obs.lost_item = self.pokemon[player2].item, self.pokemon[player2].lost_item

                            # 防御側のアイテム
                            if self.pokemon[player2].item == 'ゴツゴツメット' and not substituted and self.pokemon[player].contacts(move):
                                if self.add_hp(player, -int(self.pokemon[player].status[0]/8)):
                                    self.log[player].insert(-1, self.pokemon[player2].item)

                                    # アイテムの観測
                                    p_obs = Pokemon.find(self.observed[player2], name=self.pokemon[player2].name)
                                    p_obs.item, p_obs.lost_item = self.pokemon[player2].item, self.pokemon[player2].lost_item

                            if not substituted and self.pokemon[player2].hp:
                                match self.pokemon[player2].item:
                                    case 'きゅうこん' | 'ひかりごけ':
                                        if Pokemon.all_moves[move]['type'] == 'みず':
                                            self.consume_item(player2)
                                    case 'じゅうでんち':
                                        if Pokemon.all_moves[move]['type'] == 'でんき':
                                            self.consume_item(player2)
                                    case 'ゆきだま':
                                        if Pokemon.all_moves[move]['type'] == 'こおり':
                                            self.consume_item(player2)
                                    case 'じゃくてんほけん':
                                        if self.defence_type_correction(player, move) > 1:
                                            self.consume_item(player2)
                                    case 'ふうせん':
                                        self.consume_item(player2)
                                    case 'ナゾのみ':
                                        if self.defence_type_correction(player, move) > 1:
                                            self.consume_item(player2)
                                    case 'ジャポのみ':
                                        if Pokemon.all_moves[move]['class'] == 'phy':
                                            self.consume_item(player2)
                                    case 'レンブのみ':
                                        if Pokemon.all_moves[move]['class'] == 'spe':
                                            self.consume_item(player2)

                            # みちづれ判定
                            if self.pokemon[player2].condition['michizure']:
                                if self.pokemon[player2].hp == 0:
                                    self.pokemon[player].hp = 0
                                    self.log[player].append('瀕死 みちづれ')
                                    self.was_valid[player2] = True
                                    break
                                    
                            # 反動ダメージ
                            if move == 'わるあがき':
                                self.add_hp(player, -round_half_up(self.pokemon[player].status[0]/4), move=move)
                                self.log[player].insert(-1, '反動')
                            elif move in Pokemon.move_value['rebound'] and self.damage[player] and self.pokemon[player].ability != 'いしあたま' and \
                                self.add_hp(player, -round_half_up(self.damage[player]*Pokemon.move_value['rebound'][move])):
                                self.log[player].insert(-1, '反動')

                            # わざ効果
                            match move:
                                case 'がんせきアックス':
                                    if self.condition['stealthrock'][player2] == 0:
                                        self.condition['stealthrock'][player2] = 1
                                        self.log[player].append('追加効果 ステルスロック')
                                case 'キラースピン' | 'こうそくスピン':
                                    removed = []
                                    for s in ['yadorigi','bind']:
                                        if self.pokemon[player].condition[s]:
                                            self.pokemon[player].condition[s] = 0
                                            removed.append(s)
                                    for s in ['makibishi','dokubishi','stealthrock','nebanet']:
                                        if self.condition[s][player]:
                                            self.condition[s][player] = 0
                                            removed.append(s)
                                    if removed:
                                        self.log[player].append(f'追加効果 {[Pokemon.JPN[s] for s in removed]}解除')
                                case 'スケイルショット':
                                    if i == n_hit - 1:
                                        if self.add_rank(player, 0, 0, rank_list=[0,0,-1,0,0,1]):
                                            self.log[player].insert(-1, '追加効果')
                                case 'ひけん･ちえなみ':
                                    if self.condition['makibishi'][player2] < 3:
                                        self.condition['makibishi'][player2] = min(3, self.condition['makibishi'][player2]+1)
                                        self.log[player].append(f"追加効果 まきびし {self.condition['makibishi'][player2]}")
                                case 'プラズマフィスト':
                                    pass
                            
                            # わざ効果 (みがわりに無効化される)
                            if not substituted:
                                # バインド技
                                if move in Pokemon.move_category['bind'] and self.pokemon[player2].condition['bind'] == 0:
                                    turn = 7 if self.pokemon[player].item == 'ねばりのかぎづめ' else 5
                                    ratio = 6 if self.pokemon[player].item == 'しめつけバンド' else 8
                                    self.pokemon[player2].condition['bind'] = turn + 0.1 * ratio
                                
                                match move:
                                    case 'うちおとす' | 'サウザンアロー':
                                        if self.is_float(player2):
                                            self.pokemon[player2].condition['anti_air'] = 1
                                            self.log[player].append('追加効果 うちおとす')
                                    case 'きつけ':
                                        if self.pokemon[player2].ailment == 'PAR':
                                            self.set_ailment(player2, '')
                                            self.log[player].append('追加効果 まひ解除')
                                    case 'くらいつく':
                                        if all(not p.condition['change_block'] and 'ゴースト' not in p.types for p in self.pokemon):
                                            for j in range(2):
                                                self.pokemon[j].condition['change_block'] = 1
                                            self.log[player].append('追加効果 くらいつく')
                                    case 'サウザンウェーブ':
                                        if not self.pokemon[player2].condition['change_block']:
                                            self.pokemon[player2].condition['change_block'] = 1
                                            self.log[player].append('追加効果 にげられない')
                                    case 'ついばむ' | 'むしくい':
                                        if (item := self.pokemon[player2].item) and item[-2:] == 'のみ':
                                            self.pokemon[player2].item = ''
                                            backup = self.pokemon[player].item, self.pokemon[player].lost_item
                                            self.pokemon[player].item = item
                                            self.consume_item(player)
                                            self.pokemon[player].item, self.pokemon[player].lost_item = backup
                                            self.log[player].append(f'追加効果 {item}消費')
                                    case 'とどめばり':
                                        if self.pokemon[player2].hp == 0:
                                            if self.add_rank(player, 1, +3):
                                                self.log[player].insert(-1, '追加効果')
                                    case 'ドラゴンテール' | 'ともえなげ':
                                        commands = self.available_commands(player2, phase='change')
                                        if commands and self.pokemon[player2].is_blowable():
                                            self.change_pokemon(player2, command=self._random.choice(commands))
                                    case 'どろぼう' | 'ほしがる':
                                        if not self.pokemon[player].item and self.pokemon[player2].item and self.pokemon[player2].item_removable():
                                            self.pokemon[player].item, self.pokemon[player2].item = self.pokemon[player2].item, ''
                                            self.log[player].append(f'追加効果 {self.pokemon[player].item}奪取')
                                    case 'はたきおとす':
                                        if self.pokemon[player2].item:
                                            self.log[player].append(f'追加効果 {self.pokemon[player2].item}消失')
                                            self.pokemon[player2].item = ''
                                    case 'めざましビンタ':
                                        if self.pokemon[player2].ailment == 'SLP':
                                            self.set_ailment(player2, '')
                                            self.log[player].append('追加効果 ねむり解除')

                            # 追加効果 (処理順が遅いもの)
                            if not substituted and self.can_move_affects(player, move):
                                match move:
                                    case 'うたかたのアリア':
                                        if self.pokemon[player2].ailment == 'BRN':
                                            self.set_ailment(player2, '')
                                            self.log[player].append('追加効果 やけど解除')
                                    case 'ぶきみなじゅもん':
                                        if (ind := self.pokemon[player2].last_pp_move_index()) is not None and self.pokemon[player2].pp[ind]:
                                            self.pokemon[player2].pp[ind] = (self.pokemon[player2].pp[ind] - 3)
                                            self.log[player].append(f'追加効果 {self.pokemon[player2].moves[ind]} 残りPP {self.pokemon[player2].pp[ind]}')
                                
                            # 相手のこおり状態の解除
                            if self.pokemon[player2].ailment == 'FLZ' and self.damage[player] and \
                                (Pokemon.all_moves[move]['type'] == 'ほのお' or move in Pokemon.move_category['unfreeze']):
                                self.set_ailment(player2, '')

                    # 変化技の処理
                    else:
                        self.damage_log[player].clear()

                        # マジックミラー判定
                        pl1, pl2 = player, player2
                        if move_class[-4] == '1' and self.ability(player2, move) == 'マジックミラー':
                            pl1, pl2 = pl2, pl1
                            self.log[player].append('マジックミラー')

                            # 特性の観測
                            Pokemon.find(self.observed[player2], name=self.pokemon[player2].name).ability = \
                                self.pokemon[player2].ability

                        # みがわりによる無効
                        self.was_valid[player] = self.pokemon[pl2].sub_hp == 0 or move_class[-2] == '0'

                        # タイプ相性・特性による無効
                        if move_class[-3] == '1':
                            self.was_valid[player] &= bool(self.damage_correction(pl1, move))

                            if self.was_valid[player] and self.ability(pl2, move) == 'おうごんのからだ':
                                self.was_valid[player] = False

                                # 特性の観測
                                Pokemon.find(self.observed[player2], name=self.pokemon[player2].name).ability = \
                                    self.pokemon[player2].ability

                        if self.was_valid[player]:
                            match move:
                                case 'アクアリング':
                                    self.was_valid[player] = not self.pokemon[pl1].condition['aquaring']
                                    if self.was_valid[player]:
                                        self.pokemon[pl1].condition['aquaring'] = 1
                                case 'あくまのキッス' | 'うたう' | 'キノコのほうし' | 'くさぶえ' | 'さいみんじゅつ' | 'ダークホール' | 'ねむりごな':
                                    self.was_valid[player] = self.set_ailment(pl2, 'SLP', move)
                                case 'あくび':
                                    self.was_valid[player] = self.set_condition(pl2, 'nemuke', move) and pl2 == player2
                                case 'あさのひざし' | 'こうごうせい' | 'じこさいせい' | 'すなあつめ' | 'タマゴうみ' | 'つきのひかり' | 'なまける' | 'はねやすめ' | 'ミルクのみ':
                                    r = 0.5
                                    match move:
                                        case 'すなあつめ':
                                            if self.weather() == 'sandstorm':
                                                r = 2732/4096
                                        case 'あさのひざし' | 'こうごうせい' | 'つきのひかり':
                                            match self.weather(pl1): 
                                                case 'sunny':
                                                    r = 0.75
                                                case 'rainy' | 'snow' | 'sandstorm':
                                                    r = 0.25
                                    self.was_valid[player] = self.add_hp(pl1, round_half_down(r*self.pokemon[pl1].status[0]))

                                    if move == 'はねやすめ' and self.was_valid[player] and \
                                        not self.pokemon[pl1].terastal and 'ひこう' in self.pokemon[pl1].types:
                                        self.pokemon[pl1].lost_types.append('ひこう')

                                case 'あまいかおり':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 7, -1, by_enemy=True)) and pl2 == player2
                                case 'あまえる':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 1, -2, by_enemy=True)) and pl2 == player2
                                case 'あまごい':
                                    self.was_valid[player] = self.set_weather(pl1, 'rainy')
                                case 'あやしいひかり' | 'いばる' | 'おだてる' | 'ちょうおんぱ' | 'てんしのキッス' | 'フラフラダンス':
                                    self.was_valid[player] = self.set_condition(pl2, 'confusion')
                                    match move:
                                        case 'いばる':
                                            self.add_rank(pl2, 1, +2, by_enemy=True)
                                        case 'おだてる':
                                            self.add_rank(pl2, 3, +1, by_enemy=True)
                                case 'アロマセラピー' | 'いやしのすず':
                                    self.was_valid[player] = any([p.ailment for p in self.selected[pl1]])
                                    if self.was_valid[player]:
                                        for p in self.selected[pl1]:
                                            self.set_ailment(pl1, '')
                                case 'アンコール':
                                    self.was_valid[player] = self.pokemon[pl2].condition['encore'] == 0 and \
                                        self.ability(pl2, move) != 'アロマベール' and bool(self.pokemon[pl2].last_pp_move) and \
                                        self.pokemon[pl2].last_pp_move not in Pokemon.move_category['non_encore'] and \
                                        self.pokemon[pl2].pp[self.pokemon[pl2].last_pp_move_index()] > 0
                                    if self.was_valid[player]:
                                        self.pokemon[pl2].condition['encore'] = 3
                                        if pl2 == self.action_order[-1]:
                                            self.move[pl2] = self.pokemon[pl2].last_pp_move
                                        self.was_valid[player] = pl2 == player2
                                case 'いえき' | 'シンプルビーム' | 'なかまづくり' | 'なやみのタネ':
                                    self.was_valid[player] = not self.pokemon[pl2].has_protected_ability()
                                    if self.was_valid[player]:
                                        match move:
                                            case 'いえき':
                                                self.was_valid[player] = bool(self.pokemon[pl2].ability)
                                                self.pokemon[pl2].ability = ''
                                            case 'シンプルビーム':
                                                self.was_valid[player] = self.pokemon[pl2].ability != 'たんじゅん'
                                                self.pokemon[pl2].ability = 'たんじゅん'
                                            case 'なかまづくり':
                                                self.was_valid[player] = self.pokemon[pl1].ability != self.pokemon[pl2].ability
                                                self.pokemon[pl2].ability = self.pokemon[pl1].ability
                                            case 'なやみのタネ':
                                                self.was_valid[player] = self.pokemon[pl2].ability != 'ふみん'
                                                self.pokemon[pl2].ability = 'ふみん'
                                    self.was_valid[player] &= pl2 == player2
                                case 'いたみわけ':
                                    h = int((self.pokemon[0].hp+self.pokemon[1].hp)/2)
                                    self.was_valid[player] = h > self.pokemon[pl1].hp
                                    for j in range(2):
                                        self.add_hp(j, h - self.pokemon[j].hp, move=move)
                                    log = f'平均HP {h}'
                                case 'いとをはく' | 'こわいかお' | 'わたほうし':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 5, -2, by_enemy=True)) and pl2 == player2
                                case 'いやしのはどう' | 'フラワーヒール':
                                    r = 0.5
                                    match move:
                                        case 'いやしのはどう':
                                            if self.pokemon[pl1].ability == 'メガランチャー':
                                                r = 0.75
                                        case 'フラワーヒール':
                                            if self.condition['glassfield']:
                                                r = 0.75
                                    self.was_valid[player] = self.add_hp(pl2, round_half_up(self.pokemon[pl2].status[0]*r))
                                case 'いやなおと':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 2, -2, by_enemy=True)) and pl2 == player2
                                case 'うそなき':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 4, -2, by_enemy=True)) and pl2 == player2
                                case 'うつしえ' | 'なりきり':
                                    self.was_valid[player] = not self.pokemon[pl1].has_protected_ability() and \
                                        self.pokemon[pl2].ability not in Pokemon.ability_category['unreproducible'] and \
                                        self.pokemon[pl1].ability != self.pokemon[pl2].ability
                                    if self.was_valid[player]:
                                        self.pokemon[pl1].ability = self.pokemon[pl2].ability
                                case 'うらみ':
                                    self.was_valid[player] = (ind := self.pokemon[pl2].last_pp_move_index()) is not None and self.pokemon[pl2].pp[ind]
                                    if self.was_valid[player]:
                                        self.pokemon[pl2].pp[ind] = max(0, self.pokemon[pl2].pp[ind] - 4)
                                        self.log[player].append(f'{self.pokemon[pl2].moves[ind]} 残りPP {self.pokemon[pl2].pp[ind]}')
                                case 'エレキフィールド':
                                    self.was_valid[player] = self.set_field(pl1, 'elecfield')
                                case 'えんまく' | 'すなかけ':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 6, -1, by_enemy=True)) and pl2 == player2
                                case 'おいかぜ':
                                    self.was_valid[player] = self.condition['oikaze'][pl1] == 0
                                    if self.was_valid[player]:
                                        self.condition['oikaze'][pl1] = 4
                                        match self.pokemon[pl1].ability:
                                            case 'かぜのり':
                                                if self.add_rank(pl1, 1, +1):
                                                    self.log[player].insert(-1, self.pokemon[pl1].ability)
                                            case 'ふうりょくでんき':
                                                if not self.pokemon[pl1].condition['charge']:
                                                    self.pokemon[pl1].condition['charge'] = 1
                                                    self.log[player].append(f'{self.pokemon[pl1].ability} じゅうでん')
                                case 'オーロラベール':
                                    self.was_valid[player] = bool(self.condition['snow']) and self.condition['reflector'][pl1] == 0
                                    if self.was_valid[player]:
                                        self.condition['reflector'][pl1] = self.condition['lightwall'][pl1] = \
                                            8 if self.pokemon[pl1].item == 'ひかりのねんど' else 5
                                case 'おかたづけ' | 'りゅうのまい':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 0, 0, rank_list=[0,1,0,0,0,1]))
                                    if move == 'おかたづけ':
                                        for s in ['makibishi','dokubishi','stealthrock','nebanet']:
                                            for j in range(2):
                                                self.condition[s][j] = 0
                                case 'おきみやげ':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 0, 0, rank_list=[0,-2,0,-2], by_enemy=True))
                                    self.pokemon[pl1].hp = 0
                                case 'おたけび' | 'なみだめ':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 0, 0, rank_list=[0,-1,0,-1], by_enemy=True)) and pl2 == player2
                                case 'おにび':
                                    self.was_valid[player] = self.set_ailment(pl2, 'BRN', move)
                                case 'かいでんぱ':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 3, -2, by_enemy=True)) and pl2 == player2
                                case 'かいふくふうじ':
                                    self.was_valid[player] = self.pokemon[pl2].condition['healblock'] == 0 and self.ability(pl2, move) != 'アロマベール'
                                    if self.was_valid[player]:
                                        self.pokemon[pl2].condition['healblock'] = 5
                                        self.was_valid[player] = pl2 == player2
                                case 'かえんのまもり' | 'スレッドトラップ' | 'トーチカ' | 'ニードルガード' | 'まもる' | 'みきり':
                                    self.protect = move
                                case 'かげぶんしん':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 7, +1))
                                case 'かたくなる' | 'からにこもる' | 'まるくなる':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 2, +1))
                                case 'かなしばり':
                                    self.was_valid[player] = self.pokemon[pl2].condition['kanashibari'] == 0 and \
                                        self.pokemon[pl2].last_used_move not in ['', 'わるあがき'] and self.ability(pl2, move) != 'アロマベール'
                                    if self.was_valid[player]:
                                        self.pokemon[pl2].condition['kanashibari'] = 4
                                        self.was_valid[player] = pl2 == player2
                                case 'からをやぶる':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 0, 0, [0,2,-1,2,-1,2]))
                                case 'きあいだめ':
                                    self.was_valid[player] = self.pokemon[pl1].condition['critical'] == 0
                                    if self.was_valid[player]:
                                        self.pokemon[pl1].condition['critical'] = 2
                                case 'ギアチェンジ':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 0, 0, [0,1,0,0,0,2]))
                                case 'きりばらい':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 7, -1, by_enemy=True))
                                    for s in Pokemon.fields:
                                        self.was_valid[player] |= bool(self.condition[s])
                                        self.condition[s] = 0
                                    for s in ['reflector','lightwall','safeguard','whitemist']:
                                        self.was_valid[player] |= bool(self.condition[s][pl2])
                                        self.condition[s][pl2] = 0
                                    for s in ['makibishi','dokubishi','stealthrock','nebanet']:
                                        for j in range(2):
                                            self.was_valid[player] |= bool(self.condition[s][j])
                                            self.condition[s][j] = 0
                                    self.was_valid[player] &= pl2 == player2
                                case 'きんぞくおん':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 4, -2, by_enemy=True)) and pl2 == player2
                                case 'くすぐる':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 0, 0, [0,-1,-1])) and pl2 == player2
                                case 'グラスフィールド':
                                    self.was_valid[player] = self.set_field(pl1, 'glassfield')
                                case 'くろいきり':
                                    self.was_valid[player] = False
                                    for j in range(2):
                                        self.was_valid[player] |= any(self.pokemon[j].rank)
                                        self.pokemon[j].rank = [0]*8
                                case 'くろいまなざし' | 'とおせんぼう':
                                    self.was_valid[player] = not self.is_caught(pl2)
                                    if self.was_valid[player]:
                                        self.pokemon[pl2].condition['change_block'] = 1
                                        self.was_valid[player] = self.is_caught(pl2) and pl2 == player2
                                case 'こうそくいどう' | 'ロックカット':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 5, +2))
                                case 'コスモパワー' | 'ぼうぎょしれい':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 0, 0, [0,0,1,0,1]))
                                case 'コットンガード':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 2, +3))
                                case 'こらえる':
                                    self.koraeru = True
                                    self.was_valid[player] = False
                                case 'サイコフィールド':
                                    self.was_valid[player] = self.set_field(pl1, 'psycofield')
                                case 'さむいギャグ':
                                    self.set_weather(pl1, 'snow')
                                case 'しっぽきり':
                                    self.was_valid[player] = self.pokemon[pl1].sub_hp == 0 and \
                                        self.pokemon[pl1].hp > int(self.pokemon[pl1].status[0]/2)
                                    if self.was_valid[player]:
                                        self.add_hp(pl1, -int(self.pokemon[pl1].status[0]/2))
                                case 'しっぽをふる' | 'にらみつける':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 2, -1, by_enemy=True)) and pl2 == player2
                                case 'しびれごな' | 'でんじは' | 'へびにらみ':
                                    self.was_valid[player] = self.set_ailment(pl2, 'PAR', move)
                                case 'じこあんじ':
                                    self.was_valid[player] = self.pokemon[pl1].rank != self.pokemon[pl2].rank
                                    if self.was_valid[player]:
                                        self.pokemon[pl1].rank = self.pokemon[pl2].rank.copy()
                                case 'ジャングルヒール' | 'みかづきのいのり':
                                    self.was_valid[player] = self.add_hp(pl1, int(0.25*self.pokemon[pl1].status[0])) or self.set_ailment(pl1, '')
                                case 'じゅうでん':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 4, +1)) or not self.pokemon[pl1].condition['charge']
                                    self.pokemon[pl1].condition['charge'] = 1
                                case 'じゅうりょく':
                                    self.was_valid[player] = self.condition['gravity'] == 0
                                    if self.was_valid[player]:
                                        self.condition['gravity'] = 5
                                case 'しょうりのまい':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 0, 0, [0,1,1,0,0,1]))
                                case 'しろいきり':
                                    self.was_valid[player] = self.condition['whitemist'][pl1] == 0
                                    if self.was_valid[player]:
                                        self.condition['whitemist'][pl1] = 5
                                case 'しんぴのまもり':
                                    self.was_valid[player] = self.condition['safeguard'][pl1] == 0
                                    if self.was_valid[player]:
                                        self.condition['safeguard'][pl1] = 5
                                case 'スキルスワップ':
                                    self.was_valid[player] = not self.pokemon[pl2].has_protected_ability()
                                    if self.was_valid[player]:
                                        self.pokemon[pl1].ability,self.pokemon[pl2].ability = \
                                            self.pokemon[pl2].ability,self.pokemon[pl1].ability
                                        for pl in range(2):
                                            self.log[pl].append(f'-> {self.pokemon[pl].ability}')
                                        # 特性の再発動
                                        for j in self.speed_order:
                                            self.release_ability(j)
                                case 'すてゼリフ':
                                    self.add_rank(pl2, 0, 0, [0,-1,0,-1], by_enemy=True)
                                case 'すなあらし':
                                    self.was_valid[player] = self.set_weather(pl1, 'sandstorm')
                                case 'すりかえ' | 'トリック':
                                    self.was_valid[player] = self.pokemon[0].item_removable() and self.pokemon[1].item_removable()
                                    if self.was_valid[player]:
                                        self.pokemon[0].item, self.pokemon[1].item = self.pokemon[1].item, self.pokemon[0].item
                                        for pl in range(2):
                                            self.log[pl].append(f'-> {self.pokemon[pl].item}')
                                case 'せいちょう':
                                    v = 2 if self.weather(pl1) == 'sunny' else 1
                                    self.was_valid[player] = bool(self.add_rank(pl1, 0, 0, [0,0,0,v,v]))
                                case 'ステルスロック':
                                    pre = self.condition['stealthrock'][player2]
                                    self.condition['stealthrock'][pl2] = 1
                                    self.was_valid[player] = self.condition['stealthrock'][player2] - pre > 0
                                case 'ソウルビート':
                                    self.was_valid[player] = self.pokemon[pl1].hp > (h := int(self.pokemon[pl1].status[0]/3))
                                    if self.was_valid[player]:
                                        self.add_hp(pl1, -h)
                                        self.add_rank(pl1, 0, 0, [0]+[1]*5)
                                case 'たくわえる':
                                    self.was_valid[player] = self.pokemon[pl1].condition['stock'] < 3
                                    if self.was_valid[player]:
                                        self.pokemon[pl1].condition['stock'] += 1
                                        self.add_rank(pl1, 0, 0, [0,0,1,0,1])
                                case 'たてこもる' | 'てっぺき' | 'とける':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 2, +2))
                                case 'ちいさくなる':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 7, +2))
                                case 'ちからをすいとる':
                                    self.was_valid[player] = self.pokemon[pl2].rank[1] > -6
                                    if self.was_valid[player]:
                                        self.add_hp(pl1, self.absorbed_value(pl1, self.pokemon[pl2].status[1]*self.pokemon[pl2].rank_correction(1)))
                                        self.add_rank(pl2, 1, -1, by_enemy=True)
                                        self.was_valid[player] = pl2 == player2
                                case 'ちょうのまい':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 0, 0, [0,0,0,1,1,1]))
                                case 'ちょうはつ':
                                    self.was_valid[player] = self.pokemon[pl2].condition['chohatsu'] == 0 and \
                                        self.ability(pl2, move) not in ['アロマベール','どんかん']
                                    if self.was_valid[player]:
                                        self.pokemon[pl2].condition['chohatsu'] = 3
                                        self.was_valid[player] = pl2 == player2
                                case 'つぶらなひとみ' | 'なかよくする' | 'なきごえ':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 1, -1, by_enemy=True)) and pl2 == player2
                                case 'つぼをつく':
                                    indexes = [i for i in range(1,8) if self.pokemon[pl1].rank[i] < 6]
                                    self.was_valid[player] = bool(indexes)
                                    if self.was_valid[player]:
                                        self.add_rank(pl1, self._random.randint(1,7), +2)
                                case 'つめとぎ':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 0, 0, [0,1,0,0,0,0,1]))
                                case 'つるぎのまい':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 1, +2))
                                case 'テクスチャー':
                                    self.was_valid[player] = not self.pokemon[pl1].terastal
                                    if self.was_valid[player]:
                                        p = self.pokemon[pl1]
                                        p.lost_types += p.types
                                        p.added_types = [Pokemon.all_moves[p.moves[0]]['type']]
                                        self.log[player].append(f'-> {p.types[0]}タイプ')
                                case 'でんじふゆう':
                                    self.was_valid[player] = self.pokemon[pl1].condition['magnetrise'] == 0
                                    if self.was_valid[player]:
                                        self.pokemon[pl1].condition['magnetrise'] = 5
                                case 'とおぼえ':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 1, +1))
                                case 'どくどく' | 'どくのこな' | 'どくガス' | 'どくのいと':
                                    if move == 'どくのいと':
                                        self.add_rank(pl2, 5, -1, by_enemy=True)
                                    self.was_valid[player] = self.set_ailment(pl2, 'PSN', move, badpoison=(move=='どくどく')) and pl2 == player2
                                case 'どくびし':
                                    pre = self.condition['dokubishi'][player2]
                                    self.condition['dokubishi'][pl2] = min(2, self.condition['dokubishi'][pl2]+1)
                                    self.was_valid[player] = self.condition['dokubishi'][player2] - pre > 0
                                    self.log[player].append(f"どくびし {self.condition['dokubishi'][pl2]}")
                                case 'とぐろをまく':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 0, 0, [0,1,1,0,0,0,1]))
                                case 'トリックルーム':
                                    self.condition['trickroom'] = 5*(self.condition['trickroom'] == 0)
                                case 'ドわすれ':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 4, +2))
                                case 'ないしょばなし':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 3, -1, by_enemy=True)) and pl2 == player2
                                case 'にほんばれ':
                                    self.was_valid[player] = self.set_weather(pl1, 'sunny')
                                case 'ねがいごと':
                                    self.was_valid[player] = self.condition['wish'][player] == 0
                                    if self.was_valid[player]:
                                        self.condition['wish'][player] = 2 + 0.001 * int(self.pokemon[pl1].status[0]/2)
                                        self.log[player].append(f"ねがいごと発動")
                                case 'ねごと':
                                    self.was_valid[player] = False
                                case 'ねばねばネット':
                                    pre = self.condition['nebanet'][player2]
                                    self.condition['nebanet'][pl2] = 1
                                    self.was_valid[player] = self.condition['nebanet'][player2] - pre > 0
                                case 'ねむる':
                                    self.was_valid[player] = self.pokemon[pl1].hp < self.pokemon[pl1].status[0] and \
                                        self.pokemon[pl1].condition['healblock'] == 0 and self.set_ailment(pl1, 'SLP', move)
                                    if self.was_valid[player]:
                                        self.pokemon[pl1].hp = self.pokemon[pl1].status[0]
                                case 'ねをはる':
                                    self.was_valid[player] = not self.pokemon[pl1].condition['neoharu']
                                    if self.was_valid[player]:
                                        self.pokemon[pl1].condition['neoharu'] = 1
                                case 'のろい':
                                    if 'ゴースト' in self.pokemon[pl1].types:
                                        self.was_valid[player] = not self.pokemon[pl2].condition['noroi']
                                        if self.was_valid[player]:
                                            self.pokemon[pl2].condition['noroi'] = 1
                                            self.add_hp(pl1, -int(self.pokemon[pl1].status[0]/2))
                                    else:
                                        self.was_valid[player] = bool(self.add_rank(pl1, 0, 0, [0,1,1,0,0,-1]))
                                case 'ハートスワップ':
                                    self.was_valid[player] = self.pokemon[0].rank != self.pokemon[1].rank
                                    if self.was_valid[player]:
                                        self.pokemon[0].rank, self.pokemon[1].rank = self.pokemon[1].rank.copy(), self.pokemon[0].rank.copy()
                                case 'はいすいのじん':
                                    self.was_valid[player] = not self.pokemon[player].condition['change_block']
                                    if self.was_valid[player]:
                                        self.pokemon[player].condition['change_block'] = 1
                                        self.was_valid[player] &= bool(self.add_rank(pl1, 0, 0, [0]+[1]*5))
                                case 'ハバネロエキス':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 0, 0, [0,2,-2], by_enemy=True)) and pl2 == player2
                                case 'はらだいこ':
                                    self.was_valid[player] = self.pokemon[pl1].hp > (h := int(self.pokemon[pl1].status[0]/2))
                                    if self.was_valid[player]:
                                        self.add_hp(pl1, -h)
                                        self.was_valid[player] &= bool(self.add_rank(pl1, 1, 12))
                                case 'ひかりのかべ':
                                    self.was_valid[player] = self.condition['lightwall'][player] == 0
                                    if self.was_valid[player]:
                                        self.condition['lightwall'][player] = 8 if self.pokemon[pl1].item == 'ひかりのねんど' else 5
                                case 'ひっくりかえす':
                                    self.was_valid[player] = any(self.pokemon[pl2].rank)
                                    if self.was_valid[player]:
                                        self.pokemon[pl2].rank = [-v for v in self.pokemon[pl2].rank]
                                        self.was_valid[player] = pl2 == player2
                                        self.log[player].append(f'-> {Pokemon.rank2str(self.pokemon[pl2].rank)}')
                                case 'ビルドアップ':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 0, 0, [0,1,1]))
                                case 'フェザーダンス':
                                    self.was_valid[player] = bool(self.add_rank(pl2, 1, -2, by_enemy=True)) and pl2 == player2
                                case 'ふきとばし' | 'ほえる':
                                    commands = self.available_commands(pl2, phase='change')
                                    self.was_valid[player] = bool(commands) and self.pokemon[pl2].is_blowable()
                                    if self.was_valid[player]:
                                        self.change_pokemon(pl2, command=self._random.choice(commands))
                                        self.was_valid[player] = pl2 == player2
                                case 'ふるいたてる':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 0, 0, [0,1,0,1]))
                                case 'ブレイブチャージ' | 'めいそう':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 0, 0, [0,0,0,1,1]))
                                    if move == 'ブレイブチャージ':
                                        self.set_ailment(pl1, '')
                                case 'ほおばる':
                                    self.was_valid[player] = bool(self.pokemon[pl1].item) and self.pokemon[pl1].item[-2:] == 'のみ'
                                    if self.was_valid[player]:
                                        self.consume_item(pl1)
                                        self.add_rank(pl1, 2, +2)
                                case 'ほたるび':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 3, +3))
                                case 'ほろびのうた':
                                    for j in range(2):
                                        if self.pokemon[j].condition['horobi'] == 0:
                                            self.pokemon[j].condition['horobi'] = 4
                                    self.was_valid[player] = self.pokemon[pl2].condition['horobi'] == 4 and pl2 == player2
                                case 'まきびし':
                                    pre = self.condition['makibishi'][player2]
                                    self.condition['makibishi'][pl2] = min(3, self.condition['makibishi'][pl2]+1)
                                    self.was_valid[player] = self.condition['makibishi'][player2] - pre > 0
                                    self.log[player].append(f'まきびし {self.condition["makibishi"][pl2]}')
                                case 'まほうのこな' | 'みずびたし':
                                    t = {'まほうのこな':'エスパー', 'みずびたし':'みず'}
                                    self.was_valid[player] = not self.pokemon[pl2].terastal and self.pokemon[pl2].types != [t[move]]
                                    if self.was_valid[player]:
                                        self.pokemon[pl2].lost_types += self.pokemon[pl2].types.copy()
                                        self.pokemon[pl2].added_types = [t[move]]
                                case 'ミストフィールド':
                                    self.was_valid[player] = self.set_field(pl1, 'mistfield')
                                case 'みちづれ':
                                    self.pokemon[pl1].condition['michizure'] = True
                                case 'ミラータイプ':
                                    self.was_valid[player] = not self.pokemon[pl1].terastal and self.pokemon[pl1].types != self.pokemon[pl2].types
                                    if self.was_valid[player]:
                                        self.pokemon[pl1].lost_types += self.pokemon[pl1].types
                                        self.pokemon[pl1].added_types = self.pokemon[pl2].types
                                        self.log[player].append(f'-> {self.pokemon[pl1].types}タイプ')
                                case 'みがわり':
                                    self.was_valid[player] = self.pokemon[pl1].sub_hp == 0 and self.pokemon[pl1].hp > (h := int(self.pokemon[pl1].status[0]/4))
                                    if self.was_valid[player]:
                                        self.add_hp(pl1, -h)
                                        self.pokemon[pl1].sub_hp = h
                                case 'みをけずる':
                                    self.was_valid[player] = self.pokemon[pl1].hp > (h := int(self.pokemon[pl1].status[0]/2))
                                    if self.was_valid[player]:
                                        self.add_hp(pl1, -h)
                                        self.was_valid[player] &= bool(self.add_rank(pl1, 0, 0, [0,2,0,2,0,2]))
                                case 'メロメロ':
                                    self.was_valid[player] = self.set_condition(pl2, 'meromero') and pl2 == player2
                                case 'もりののろい':
                                    self.was_valid[player] = not self.pokemon[pl2].terastal and 'くさ' not in self.pokemon[pl2].types
                                    if self.was_valid[player]:
                                        self.pokemon[pl2].added_types.append('くさ')
                                case 'やどりぎのタネ':
                                    self.was_valid[player] = not self.pokemon[pl2].condition['yadorigi'] and 'くさ' not in self.pokemon[pl2].types
                                    if self.was_valid[player]:
                                        self.pokemon[pl2].condition['yadorigi'] = 1
                                        self.was_valid[player] = pl2 == player2
                                case 'ゆきげしき':
                                    self.was_valid[player] = self.set_weather(pl1, 'snow')
                                case 'リサイクル':
                                    self.was_valid[player] = not self.pokemon[pl1].item and bool(self.pokemon[pl1].lost_item)
                                    if self.was_valid[player]:
                                        self.pokemon[pl1].item, self.pokemon[pl1].lost_item = self.pokemon[pl1].lost_item, ''
                                        self.log[player].append(f'{self.pokemon[pl1].item}回収')
                                case 'リフレクター':
                                    self.was_valid[player] = self.condition['reflector'][player] == 0
                                    if self.was_valid[player]:
                                        self.condition['reflector'][player] = 8 if self.pokemon[pl1].item == 'ひかりのねんど' else 5
                                case 'リフレッシュ':
                                    self.was_valid[player] = bool(self.pokemon[pl1].ailment)
                                    if self.was_valid[player]:
                                        self.set_ailment(pl1, '')
                                case 'ロックオン':
                                    self.was_valid[player] = not self.pokemon[pl1].lockon
                                    self.pokemon[pl1].lockon = True
                                case 'わるだくみ':
                                    self.was_valid[player] = bool(self.add_rank(pl1, 3, +2))

                    # 特性による無効化後の処理
                    ability = ''
                    (pl1, pl2) = (player2, player) if 'マジックミラー' in self.damage_log[player] else (player, player2)
                    for s in ['かんそうはだ','ちくでん','ちょすい','どしょく']:
                        if s in self.damage_log[pl1]:
                            self.damage_log[pl1].remove(s)
                            if self.add_hp(pl2, int(self.pokemon[pl2].status[0]/4)):
                                self.log[pl2].insert(-1, s)
                            ability = s
                            break
                    for s in ['かぜのり','そうしょく']:
                        if s in self.damage_log[pl1]:
                            self.damage_log[pl1].remove(s)
                            if self.add_rank(pl2, 1, +1):
                                self.log[pl2].insert(-1, s)
                            ability = s
                            break
                    if 'こんがりボディ' in self.damage_log[pl1]:
                        self.damage_log[pl1].remove('こんがりボディ')
                        if self.add_rank(pl2, 2, +2):
                            self.log[pl2].insert(-1, 'こんがりボディ')
                        ability = s
                    for s in ['ひらいしん','よびみず']:
                        if s in self.damage_log[pl1]:
                            self.damage_log[pl1].remove(s)
                            if self.add_rank(pl2, 3, +1):
                                self.log[pl2].insert(-1, s)
                                break
                        ability = s
                    if 'でんきエンジン' in self.damage_log[pl1]:
                        self.damage_log[pl1].remove('でんきエンジン')
                        if self.add_rank(pl2, 5, +1):
                            self.log[pl2].insert(-1, 'でんきエンジン')
                        ability = s
                    if 'もらいび' in self.damage_log[pl1]:
                        self.damage_log[pl1].remove('もらいび')
                        self.pokemon[pl2].ability += '+'
                        ability = s

                    # 特性の観測
                    if ability:
                        Pokemon.find(self.observed[pl2], name=self.pokemon[pl2].name).ability = \
                        self.pokemon[pl2].ability

                    # 即時発動アイテムの判定 (攻撃中)
                    for j in [player, player2]:
                        if self.pokemon[player].hp:
                            self.use_immediate_item(j)

                    # どちらか一方が瀕死になったら攻撃を中断
                    if self.pokemon[player].hp == 0 or self.pokemon[player2].hp == 0:
                        break
                        
                ### わざ発動後の処理
                self.pokemon[player].acted_turn += 1
                self.log[player].append(f"{move} {'成功' if self.was_valid[player] else '失敗'}")

                # ステラ
                if self.damage[player] and self.pokemon[player].Ttype == 'ステラ' and self.pokemon[player].terastal:
                    if move == 'テラバースト':
                        # テラバーストのランク下降
                        if self.add_rank(player, 0, 0, rank_list=[0,-1,0,-1]):
                            self.log[player].insert(-1, '追加効果')
                    elif ((t := Pokemon.all_moves[move]['type']) in self.stellar[player]) and 'テラパゴス' not in self.pokemon[player].name:
                        # 一度強化したタイプをリストから削除
                        self.stellar[player].remove(t)
                        self.log[player].append(f"ステラ {t}消費")

                # 反動で動けない技
                if move in Pokemon.move_category['immovable'] and self.was_valid[player]:
                    self.pokemon[player].inaccessible = 1

                # 攻撃側の特性
                if self.damage[player]:
                    observed = False

                    match self.pokemon[player].ability:
                        case 'じしんかじょう' | 'しろのいななき':
                            if not self.pokemon[player2].hp and self.add_rank(player, 1, +1):
                                self.log[player].insert(-1, self.pokemon[player].ability)
                                observed = True
                        case 'じんばいったい':
                            ind = 1 if 'はくば' in self.pokemon[player].name else 3
                            if not self.pokemon[player2].hp and self.add_rank(player, ind, +1):
                                self.log[player].insert(-1, self.pokemon[player].ability)
                                observed = True
                        case 'くろのいななき':
                            if not self.pokemon[player2].hp and self.add_rank(player, 3, +1):
                                self.log[player].insert(-1, self.pokemon[player].ability)
                                observed = True
                        case 'マジシャン':
                            if not self.pokemon[player].item and self.pokemon[player2].item:
                                self.pokemon[player].item, self.pokemon[player2].item = self.pokemon[player2].item, ''
                                self.log[player].append(f'{self.pokemon[player].ability} {self.pokemon[player].item}奪取')
                                observed = True

                    # 特性の観測
                    if observed:
                        Pokemon.find(self.observed[player], name=self.pokemon[player].name).ability = \
                            self.pokemon[player].ability

                # 防御側の特性
                if self.damage[player]:
                    observed = False

                    match self.pokemon[player2].ability:
                        case 'へんしょく':
                            if self.pokemon[player2].types != [Pokemon.all_moves[move]['type']]:
                                self.pokemon[player2].lost_types += self.pokemon[player2].types
                                self.pokemon[player2].added_types = [Pokemon.all_moves[move]['type']]
                                self.log[player2].append(f"{self.pokemon[player2].ability} -> {Pokemon.all_moves[move]['type']}")
                                observed = True
                        case 'ぎゃくじょう':
                            if self.pokemon[player2].berserk_triggered and self.add_rank(player2, 3, +1):
                                self.log[player].insert(-1, self.pokemon[player2].ability)
                                observed = True
                        case 'いかりのこうら':
                            if self.pokemon[player2].berserk_triggered and self.add_rank(player2, 0, 0, [0,1,-1,1,-1,1]):
                                self.log[player2].insert(-1, self.pokemon[player2].ability)
                                observed = True

                    self.pokemon[player2].berserk_triggered = False

                    # 特性の観測
                    if observed:
                        Pokemon.find(self.observed[player2], name=self.pokemon[player2].name).ability = \
                            self.pokemon[player2].ability


                # 被弾時に発動するアイテム
                if self.damage[player] and self.pokemon[player2].hp:
                    match self.pokemon[player2].item:
                        case 'レッドカード':
                            if self.available_commands(player, phase='change'):
                                self.consume_item(player2)
                        case 'アッキのみ':
                            if Pokemon.all_moves[move]['class'] == 'phy':
                                self.consume_item(player2)
                        case 'タラプのみ':
                            if Pokemon.all_moves[move]['class'] == 'spe':
                                self.consume_item(player2)

                observed = False

                match self.pokemon[player].item:
                    case 'いのちのたま':
                        if self.damage[player] and self.add_hp(player, -int(self.pokemon[player].status[0]/10)):
                            self.log[player].insert(-1, self.pokemon[player].item)
                            observed = True
                    case 'かいがらのすず':
                        if self.add_hp(player, int(self.damage[player]/8)):
                            self.log[player].insert(-1, self.pokemon[player].item)
                            observed = True

                # アイテムの観測
                if observed:
                    Pokemon.find(self.observed[player], name=self.pokemon[player].name).item = \
                        self.pokemon[player].item

                # ききかいひ・にげごし判定
                # わるいてぐせ判定

                # だっしゅつボタン判定
                if self.pokemon[player2].item == 'だっしゅつボタン' and self.damage[player] and \
                    self.changeable_indexes(player2):
                    self.breakpoint[player2] = 'ejectbutton'
                    self.consume_item(player2)
            
            # だっしゅつボタンによる交代
            ejectbutton_triggered = False
            if self.breakpoint[player2] == 'ejectbutton':
                self.change_pokemon(player2, command=change_commands[player2])
                change_commands[player2] = None # コマンド破棄
                ejectbutton_triggered = True

            if not any(self.breakpoint):
                # 技の効果 (追加効果ではない)
                match move:
                    case 'アイアンローラー' | 'アイススピナー':
                        if (field := self.field()):
                            self.set_field(0, field='')
                            self.log[player].append(f'追加効果 {Pokemon.JPN[field]}消滅')
                    case 'クイックターン' | 'とんぼがえり' | 'ボルトチェンジ' | 'さむいギャグ' | 'しっぽきり' | 'テレポート' | 'バトンタッチ' | 'すてゼリフ':
                        if move in ['クイックターン', 'とんぼがえり', 'ボルトチェンジ'] and ejectbutton_triggered:
                            self.log[player].append(f'交代失敗')
                        elif self.was_valid[player]:
                            pl = player2 if move == 'すてゼリフ' and move_class[-4] == '1' and self.ability(player2, move) == 'マジックミラー' else player
                            if self.changeable_indexes(pl):
                                self.breakpoint[pl] = f'Uturn_{player}'
                    case 'でんこうそうげき' | 'もえつきる':
                        t = {'でんこうそうげき':'でんき', 'もえつきる':'ほのお'}
                        self.pokemon[player].lost_types.append(t[move])
                        self.log[player].append(f'追加効果 {t[move]}タイプ消失')

            # 技による交代
            Uturned = False

            if (s := f'Uturn_{player}') in self.breakpoint:
                pl = self.breakpoint.index(s)
                baton = {}
                
                match move:
                    case 'しっぽきり':
                        baton['sub_hp'] = int(self.pokemon[pl].status[0]/4)
                    case 'バトンタッチ':
                        if any(self.pokemon[pl].rank):
                            baton['rank'] = self.pokemon[pl].rank.copy()
                        if self.pokemon[pl].sub_hp:
                            baton['sub_hp'] = self.pokemon[pl].sub_hp
                        for s in list(self.pokemon[pl].condition.keys())[:8]:
                            if self.pokemon[pl].condition[s]:
                                baton[s] = self.pokemon[pl].condition[s]
                
                self.change_pokemon(pl, command=change_commands[pl], baton=baton)
                change_commands[pl] = None # コマンド破棄
                Uturned = True
            
            if not any(self.breakpoint):
                if not ejectbutton_triggered and not Uturned:
                    # だっしゅつパック判定 (わざ発動後)
                    players = [pl for pl in self.speed_order if self.pokemon[pl].item == 'だっしゅつパック' and \
                        self.pokemon[pl].rank_dropped and self.changeable_indexes(pl)]
                    if players:
                        self.breakpoint[players[0]] = f'ejectpack_move_{player}'
                        self.consume_item(players[0])
                        for pl in players:
                            self.pokemon[pl].rank_dropped = False

            # だっしゅつパックによる交代
            if (s := f'ejectpack_move_{player}') in self.breakpoint:
                pl = self.breakpoint.index(s)
                self.change_pokemon(pl, command=change_commands[pl])
                change_commands[pl] = None # コマンド破棄

            if not any(self.breakpoint):
                # あばれる状態の判定
                if move in Pokemon.move_category['continuous']:
                    if self.pokemon[player].inaccessible == 0:
                        self.pokemon[player].inaccessible = self._random.randint(1,2)
                        self.log[player].append(f'{move} 残り{self.pokemon[player].inaccessible}ターン')
                    else:
                        self.pokemon[player].inaccessible -= 1
                        if self.pokemon[player].inaccessible:
                            self.log[player].append(f'{move} 残り{self.pokemon[player].inaccessible}ターン')
                        else:
                            if self.set_condition(player, 'confusion'):
                                self.log[player].append(f'{move}解除 こんらん')

                if self.pokemon[player].hp and self.pokemon[player].item == 'のどスプレー' and \
                    self.pokemon[player].last_used_move in Pokemon.move_category['sound']:
                    self.consume_item(player)

                # 即時発動アイテムの判定 (手番が移る直前)
                if self.pokemon[player].hp:
                    self.use_immediate_item(player)

                # 先手が後手を倒したら中断
                if self.pokemon[not player].hp == 0:
                    break

        ### ターン終了時の処理
        if not any(self.breakpoint):
            if self.winner(record=True) is not None: # 勝敗判定
                return

            # 天候カウント
            for s in Pokemon.weathers:
                if self.condition[s]:
                    self.condition[s] -= 1
                    if self.condition[s] == 0:
                        self.set_weather(0, weather='')
                    self.log[player].append(f'{Pokemon.JPN[s]} 残り{self.condition[s]}ターン')
            
            # 砂嵐ダメージ
            if self.weather() == 'sandstorm':
                for player in self.speed_order:
                    p = self.pokemon[player]
                    if not p.hp:
                        continue

                    if any(s in p.types for s in ['いわ','じめん','はがね']) or \
                        p.ability in ['すなかき','すながくれ','すなのちから'] or \
                        self.is_overcoat(player) or p.hide_move in ['あなをほる','ダイビング']:
                        continue

                    if self.add_hp(player, -int(p.status[0]/16)):
                        self.log[player].insert(-1, 'すなあらし')
                        if self.pokemon[player].hp == 0 and self.winner(record=True) is not None: # 勝敗判定
                            return

            # 天候に関する特性
            for player in self.speed_order:
                p = self.pokemon[player]
                observed = False

                if p.hide_move in ['あなをほる','ダイビング']:
                    continue

                match self.weather(player) * bool(p.hp):
                    case 'sunny':
                        if p.ability in ['かんそうはだ','サンパワー'] and self.add_hp(player, -int(p.status[0]/8)):
                            self.log[player].insert(-1, p.ability)
                            if self.pokemon[player].hp == 0 and self.winner(record=True) is not None: # 勝敗判定
                                return
                            observed = True

                    case 'rainy':
                        match p.ability:
                            case 'あめうけざら':
                                if self.add_hp(player, int(p.status[0]/16)):
                                    self.log[player].insert(-1, p.ability)
                                    observed = True
                            case 'かんそうはだ':
                                if self.add_hp(player, int(p.status[0]/8)):
                                    self.log[player].insert(-1, p.ability)
                                    observed = True
        
                    case 'snow':
                        if p.ability == 'アイスボディ' and self.add_hp(player, int(p.status[0]/16)):
                            self.log[player].insert(-1, p.ability)
                            observed = True

                # 特性の観測
                if observed:
                    Pokemon.find(self.observed[player], name=self.pokemon[player].name).ability = \
                        self.pokemon[player].ability

            if self.winner(record=True) is not None: # 勝敗判定
                return

            # ねがいごと
            for player in self.speed_order:
                if self.condition['wish'][player]:
                    self.condition['wish'][player] -= 1
                    self.log[player].append(f"ねがいごと 残り{int(self.condition['wish'][player])}ターン")
                    if int(self.condition['wish'][player]) == 0:
                        self.add_hp(player, 1000*frac(self.condition['wish'][player]))
                        self.condition['wish'][player] = 0

            # グラスフィールド回復
            if self.condition['glassfield']:
                for player in self.speed_order:
                    if p.hide_move in ['あなをほる','ダイビング']:
                        continue
                    elif self.pokemon[player].hp and not self.is_float(player) and \
                        self.add_hp(player, int(p.status[0]/16)):
                        self.log[player].insert(-1, 'グラスフィールド')

            # うるおいボディ等
            for player in self.speed_order:
                if self.pokemon[player].ailment and self.pokemon[player].hp:
                    observed = False

                    match p.ability:
                        case 'うるおいボディ':
                            if self.condition['rainy']:
                                self.set_ailment(player, '')
                                self.log[player].insert(-1, p.ability)
                                self.pokemon[player].ailment = ''
                                observed = True
                        case 'だっぴ':
                            if self._random.random() < 0.3:
                                self.set_ailment(player, '')
                                self.log[player].insert(-1, p.ability)
                                observed = True
                
                    # 特性の観測
                    if observed:
                        Pokemon.find(self.observed[player], name=self.pokemon[player].name).ability = \
                            self.pokemon[player].ability

            # たべのこし
            for player in self.speed_order:
                p = self.pokemon[player]
                observed = False

                match p.item * bool(p.hp):
                    case 'たべのこし':
                        if self.add_hp(player, int(p.status[0]/16)):
                            self.log[player].insert(-1, p.item)
                            observed = True

                    case 'くろいヘドロ':
                        r = 1 if 'どく' in p.types else -1
                        if self.add_hp(player, (h := int(p.status[0]/16)*r)):
                            self.log[player].insert(-1, p.item)
                            if h < 0 and self.pokemon[player].hp == 0 and self.winner(record=True) is not None: # 勝敗判定
                                return
                            observed = True

                # アイテムの観測
                if observed:
                    Pokemon.find(self.observed[player], name=self.pokemon[player].name).item = \
                        self.pokemon[player].item

            # アクアリング・ねをはる
            for player in self.speed_order:
                p = self.pokemon[player]
                if not p.hp:
                    continue
                h = self.absorbed_value(player, int(p.status[0]/16), from_enemy=False)
                for s in ['aquaring', 'neoharu']:
                    if p.condition[s] and self.add_hp(player, h):
                        self.log[player].insert(-1, s)

            # やどりぎのタネ
            for player in self.speed_order:
                player2 = not player
                p1 = self.pokemon[player]
                p2 = self.pokemon[player2]
                if p1.condition['yadorigi'] and p1.hp*p2.hp:
                    d = -min(p1.hp, int(p1.status[0]/16))
                    if self.add_hp(player, d):
                        self.log[player].insert(-1, 'やどりぎのタネ')
                        if self.winner(record=True) is not None: # 勝敗判定
                            return
                        if self.add_hp(player2, self.absorbed_value(player2, -d)):
                            self.log[player2].insert(-1, 'やどりぎのタネ')
                            if h < 0 and self.pokemon[player].hp == 0 and self.winner(record=True) is not None: # 勝敗判定
                                return

            # 状態異常ダメージ
            for player in self.speed_order:
                p = self.pokemon[player]
                if not p.hp:
                    continue

                match p.ailment:
                    case 'PSN':
                        if p.ability == 'ポイズンヒール':
                            if self.add_hp(player, int(p.status[0]/8)):
                                self.log[player].insert(-1, p.ability)
                            Pokemon.find(self.observed[player], name=p.name).ability = p.ability

                        elif p.condition['badpoison']:
                            if self.add_hp(player, -int(p.status[0]/16*p.condition['badpoison'])):
                                self.log[player].insert(-1, 'もうどく')
                                if self.pokemon[player].hp == 0 and self.winner(record=True) is not None: # 勝敗判定
                                    return
                        else:
                            if self.add_hp(player, -int(p.status[0]/8)):
                                self.log[player].insert(-1, 'どく')
                                if self.pokemon[player].hp == 0 and self.winner(record=True) is not None: # 勝敗判定
                                    return
                        if p.condition['badpoison']:
                            p.condition['badpoison'] += 1
                    case 'BRN':
                        r = 32 if self.pokemon[player].ability == 'たいねつ' else 16
                        if self.add_hp(player, -int(p.status[0]/r)):
                            self.log[player].insert(-1, 'やけど')
                            if self.pokemon[player].hp == 0 and self.winner(record=True) is not None: # 勝敗判定
                                return

            # 呪いダメージ
            for player in self.speed_order:
                p = self.pokemon[player]
                if p.condition['noroi'] and p.hp and self.add_hp(player, -int(p.status[0]/4)):
                    self.log[player].insert(-1, '呪い')
                    if self.pokemon[player].hp == 0 and self.winner(record=True) is not None: # 勝敗判定
                        return

            # バインドダメージ
            for player in self.speed_order:
                p = self.pokemon[player]
                if p.condition['bind'] and p.hp:
                    p.condition['bind'] -= 1
                    self.log[player].append(f"バインド 残り{int(p.condition['bind'])}ターン")
                    if self.add_hp(player, -int(p.status[0]/10/frac(p.condition['bind']))):
                        self.log[player].insert(-1, 'バインド')
                        if self.pokemon[player].hp == 0 and self.winner(record=True) is not None: # 勝敗判定
                            return
                    if int(p.condition['bind']) == 0:
                        p.condition['bind'] = 0

            # しおづけダメージ
            for player in self.speed_order:
                p = self.pokemon[player]
                if p.condition['shiozuke'] and p.hp:
                    r = 2 if any(t in p.types for t in ['みず','はがね']) else 1
                    if self.add_hp(player, -int(p.status[0]/8*r)):
                        self.log[player].insert(-1, 'しおづけ')
                        if self.pokemon[player].hp == 0 and self.winner(record=True) is not None: # 勝敗判定
                            return
                
            # あめまみれ
            for player in self.speed_order:
                p = self.pokemon[player]
                if p.condition['ame_mamire'] and p.hp and self.add_rank(player, 5, -1):
                    p.condition['ame_mamire'] -= 1
                    self.log[player].append(f"あめまみれ 残り{p.condition['ame_mamire']}ターン")

            if self.winner(record=True) is not None: # 勝敗判定
                return

            # 状態変化カウント
            for player in self.speed_order:
                p = self.pokemon[player]
                if not p.hp:
                    continue
                
                for s in ['encore','healblock','kanashibari','jigokuzuki','chohatsu','magnetrise']:
                    if p.condition[s]:
                        p.condition[s] -= 1
                        self.log[player].append(f'{Pokemon.JPN[s]} 残り{p.condition[s]}ターン')
                
                # PPが切れたらアンコール解除
                if p.condition['encore'] and (ind := p.last_pp_move_index()) is not None and p.pp[ind] == 0:
                    p.condition['encore'] = 0
                    self.log[player].append(f'{p.moves[ind]} PP切れ アンコール解除')

            # ねむけ判定
            for player in self.speed_order:
                p = self.pokemon[player]
                if p.condition['nemuke']:
                    p.condition['nemuke'] -= 1
                    self.log[player].append(f"ねむけ 残り{p.condition['nemuke']}ターン")
                    if p.condition['nemuke'] == 0:
                        self.set_ailment(player, 'SLP', safeguard=False)

            # ほろびのうた判定
            for player in self.speed_order:
                p = self.pokemon[player]
                if p.hp and p.condition['horobi']:
                    p.condition['horobi'] -= 1
                    if p.condition['horobi'] > 0:
                        self.log[player].append(f"ほろびのうた 残り{p.condition['horobi']}ターン")
                    else:
                        p.hp = 0
                        self.log[player].append('ほろびのうた 瀕死')
                        if self.winner(record=True) is not None: # 勝敗判定
                            return

            # 場の効果の終了
            for player in self.speed_order:
                for s in ['reflector','lightwall','safeguard','whitemist','oikaze']:
                    if self.condition[s][player]:
                        self.condition[s][player] -= 1
                        self.log[player].append(f'{Pokemon.JPN[s]} 残り{self.condition[s][player]}ターン')

            for s in list(self.condition.keys())[4:10]:
                if self.condition[s]:
                    self.condition[s] -= 1
                    if s in Pokemon.fields and self.condition[s] == 0:
                        self.set_field(0, field='')
                    for player in self.speed_order:
                        self.log[player].append(f'{Pokemon.JPN[s]} 残り{self.condition[s]}ターン')

            # 即時発動アイテムの判定 (ターン終了時)
            if self.pokemon[player].hp:
                self.use_immediate_item(player)

            # はねやすめ解除
            for player in self.speed_order:
                if self.pokemon[player].last_used_move == 'はねやすめ' and self.was_valid[player] and \
                    'ひこう' in self.pokemon[player].lost_types:
                    self.pokemon[player].lost_types.remove('ひこう')
                    self.log[player].append('はねやすめ解除')

            # その他
            for player in self.speed_order:
                p1 = self.pokemon[player]
                if not p1.hp:
                    continue

                player2 = not player
                p2 = self.pokemon[player2]
                observed = False
                
                if 'スロースタート' in p1.ability or 'はんすう+' in p1.ability:
                    p1.ability += '+'

                match p1.ability:
                    case 'かそく':
                        if self.pokemon[player].acted_turn and self.add_rank(player, 5, +1):
                            self.log[player].insert(-1, p1.ability)
                            observed = True
                    case 'しゅうかく':
                        if not p1.item and p1.lost_item[-2:] == 'のみ' and \
                            (self.condition['sunny'] or self._random.random() < 0.5):
                            p1.item, p1.lost_item = p1.lost_item, ''
                            self.log[player].append(f'{p1.ability} {p1.item}回収')
                            observed = True
                    case 'ムラっけ':
                        ind = 0
                        inds = [i for i in range(1,6) if p1.rank[i] < 6]
                        if inds:
                            ind = self._random.choice(inds)
                            if self.add_rank(player, ind, +2):
                                self.log[player].insert(-1, p1.ability)
                        inds = [i for i in range(1,6) if p1.rank[i] > -6]
                        if ind in inds:
                            inds.remove(ind)
                        if inds:
                            self.add_rank(player, self._random.choice(inds), -1)
                        observed = True
                    case 'ナイトメア':
                        if p2.ailment == 'SLP' and self.add_hp(player2, -int(p2.status[0]/8)):
                            self.log[player].append(p1.ability)
                            observed = True
                            if self.winner(record=True) is not None: # 勝敗判定
                                return
                    case 'はんすう+++':
                        if p1.lost_item[-2:] == 'のみ':
                            self.log[player].append('はんすう')
                            backup = p1.item
                            p1.item, p1.lost_item = p1.lost_item, ''
                            self.consume_item(player)
                            p1.item = backup

                # 特性の観測
                if observed:
                    Pokemon.find(self.observed[player], name=p1.name).ability = p1.ability

                observed = False
                match p1.item:
                    case 'かえんだま':
                        if self.set_ailment(player, 'BRN', safeguard=False):
                            self.log[player].insert(-1, f'{p1.item}発動')
                            observed = True
                    case 'どくどくだま':
                        if self.set_ailment(player, 'PSN', badpoison=True, safeguard=False):
                            self.log[player].insert(-1, f'{p1.item}発動')
                            observed = True

                if observed:
                    Pokemon.find(self.observed[player], name=p1.name).item = p1.item

            if self.winner(record=True) is not None: # 勝敗判定
                return

            # だっしゅつパック判定 (ターン終了時)
            players = [pl for pl in self.speed_order if self.pokemon[pl].item == 'だっしゅつパック' and \
                        self.pokemon[pl].rank_dropped and self.changeable_indexes(pl)]
            if players:
                self.breakpoint[players[0]] = 'ejectpack_end'
                self.consume_item(players[0])
                for pl in players:
                    self.pokemon[pl].rank_dropped = False

        # だっしゅつパックによる交代
        if (s := 'ejectpack_end') in self.breakpoint:
            player = self.breakpoint.index(s)
            self.change_pokemon(player, command=change_commands[player])
            change_commands[player] = None # コマンド破棄
        
        # 場のポケモンが瀕死なら交代
        while self.winner(record=True) is None:
            players = []

            # 交代するプレイヤーを取得
            if not any(self.breakpoint):
                players = [player for player in range(2) if self.pokemon[player].hp == 0]
                for player in players:
                    self.breakpoint[player] = 'death'
            else:
                players = [player for player in range(2) if self.breakpoint[player] == 'death']

            if not players:
                break
            
            # 交代
            for player in players:
                self.change_pokemon(player, command=change_commands[player], landing=False)
                change_commands[player] = None # コマンド破棄
            
            # 両者が死に出しした場合は素早さ順に処理する
            if len(players) == 2:
                players = self.speed_order

            # 着地処理
            for player in players:
                self.land(player)

        # このターンに入力されたコマンドをログに記録
        self.record_command()
