from pokepy.pokemon import *
import cv2
import glob
import os
import pyocr, pyocr.builders
from PIL import Image
import time
import Levenshtein
import json
import glob
import jaconv
import shutil

is_linux = (os.name != 'nt')
if is_linux:
    import nxbt


TESSERACT_PATH = os.getcwd()+'/Tesseract-OCR'
TESSDATA_PATH = TESSERACT_PATH + '/tessdata'
os.environ["PATH"] += os.pathsep + TESSERACT_PATH
os.environ["TESSDATA_PREFIX"] = TESSDATA_PATH


def rect_trim(img, threshold=255):
    h, w = img.shape[0], img.shape[1]
    w_min, w_max, h_min, h_max = int(w*0.5), int(w*0.5), int(h*0.5), int(h*0.5)
    for h in range(len(img)):
        for w in range(len(img[0])):
            if img[h][w][0] < threshold or img[h][w][1] < threshold or img[h][w][2] < threshold:
                w_min = min(w_min, w)
                w_max = max(w_max, w)
                h_min = min(h_min, h)
                h_max = max(h_max, h)
    return img[h_min:h_max+1, w_min:w_max+1]

def cv2pil(image):
    new_image = image.copy()
    if new_image.ndim == 2:  # モノクロ
        pass
    elif new_image.shape[2] == 3:  # カラー
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGR2RGB)
    elif new_image.shape[2] == 4:  # 透過
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGRA2RGBA)
    new_image = Image.fromarray(new_image)
    return new_image

def BGR2BIN(img, threshold=128, bitwise_not=False):
    img1 = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, img1 = cv2.threshold(img1, threshold, 255, cv2.THRESH_BINARY)
    if bitwise_not:
        img1 = cv2.bitwise_not(img1)
    return img1

def most_similar_element(str_list, s):
    if s in str_list:
        return s
    s1 = jaconv.hira2kata(s)
    distances = [Levenshtein.distance(s1, jaconv.hira2kata(s)) for s in str_list]
    return str_list[distances.index(min(distances))]

def template_match_score(img, template):
    result = cv2.matchTemplate(img, template, cv2.TM_CCORR_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return max_val

def to_jpn_upper(s):
    trans = str.maketrans('ぁぃぅぇぉっゃゅょァィゥェォッャュョ', 'あいうえおつやゆよアイウエオツヤユヨ')
    return s.translate(trans)

def OCR(img, lang='jpn', candidates=[], log_dir='', scale=1):
    result = ''
    
    # OCR履歴と照合
    if is_linux and log_dir:
        os.makedirs(log_dir, exist_ok=True)
        if log_dir[-1] != '/':
            log_dir += '/'
        for s in glob.glob(log_dir + '*'):
            template = cv2.cvtColor(cv2.imread(s), cv2.COLOR_BGR2GRAY)
            if template_match_score(img, template) > 0.99:
                result = os.path.splitext(os.path.basename(s))[0]
    
    # 履歴に合致しなければOCR
    if not result:
        builder = pyocr.builders.TextBuilder(tesseract_layout=7)
        match lang:
            case 'all':
                lang = 'jpn+chi+kor+eng'#+fra+deu'
            case 'num':
                lang = 'eng'
                builder = pyocr.builders.DigitBuilder(tesseract_layout=7)
        if scale > 1:
            img = cv2.resize(img, (img.shape[1]*scale, img.shape[0]*scale), interpolation=cv2.INTER_CUBIC)
        tools = pyocr.get_available_tools()
        result = tools[0].image_to_string(cv2pil(img), lang=lang, builder=builder)
        #print(f'\t\tOCR: {result}')
        if result and log_dir:
            cv2.imwrite(log_dir+result+'.png', img) # 履歴に追加
    if len(candidates):
        result = most_similar_element(candidates, result)
    
    return result


# キャプチャ設定
cap = None
if is_linux:
    print('config.txt')
    with open('config.txt') as fin:
        line = fin.readline()
        video_id = int(line.split()[1])
        print(f'\tVideo ID: {video_id}')

        print('キャプチャデバイスを接続中...')
        cap = cv2.VideoCapture(video_id)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)


class Pokebot(Battle):
    is_init = False

    img = None
    phase = ''
    vs_NPC = True

    selection_command_time = 10 # 選出のコマンド入力にかかる時間の初期値
    battle_command_time = 10    # ターンのコマンド入力にかかる時間の初期値
    change_command_time = 3     # 交代のコマンド入力にかかる時間の初期値

    GAME_TIME_MINUIT = 20

    PRESS_INTERVAL = 0.2        # 決定ボタンの入力間隔
    CAPTURE_TIME = 0.1          # ボタン入力からキャプチャまでの待ち時間
    TRANS_CAPTURE_TIME = 0.3    # ボタン入力からキャプチャまでの待ち時間 (画面遷移あり)
    ADDITIONAL_TIME = 0.5       # 一部の画面遷移時に追加する待ち時間

    # nxbt
    nx, nxid = None, None

    # テンプレート画像の読み込み
    templ_battle = BGR2BIN(cv2.imread('data/screen/battle.png'), threshold=200, bitwise_not=True)
    templ_change = BGR2BIN(cv2.imread('data/screen/change.png'), threshold=150, bitwise_not=True)
    templ_selection = BGR2BIN(cv2.imread('data/screen/selection.png'), threshold=100, bitwise_not=True)
    templ_standby = BGR2BIN(cv2.imread('data/screen/standby.png'), threshold=100, bitwise_not=True)
    templ_condition_window = BGR2BIN(cv2.imread('data/screen/condition.png'), threshold=200, bitwise_not=True)
    templ_dead_enemy = BGR2BIN(cv2.imread('data/screen/dead_enemy.png'), threshold=128)

    templ_alives = {}
    for s in ['alive', 'dead', 'in_battle']:
        templ_alives[s] = BGR2BIN(cv2.imread(f'data/screen/{s}.png'), threshold=150, bitwise_not=True)
    
    templ_winlose = {}
    for s in ['win','lose']:
        templ_winlose[s] = BGR2BIN(cv2.imread(f'data/screen/{s}.png'), threshold=140, bitwise_not=True)

    templ_condition_turns = []
    for i in range(8):
        s = str(i+1)
        img = BGR2BIN(cv2.imread(f'data/condition/turn/{s}.png'), threshold=128)
        if cv2.countNonZero(img)/img.size < 0.5:
            img = cv2.bitwise_not(img)
        templ_condition_turns.append(img)
    
    templ_condition_counts = []
    for i in range(3):
        s = str(i+1)
        img = BGR2BIN(cv2.imread(f'data/condition/count/{s}.png'), threshold=128)
        if cv2.countNonZero(img)/img.size < 0.5:
            img = cv2.bitwise_not(img)
        templ_condition_counts.append(img)

    templ_condition_horobis = []
    for i in range(3):
        s = str(i+1)
        img = BGR2BIN(cv2.imread(f'data/condition/horobi/{s}.png'), threshold=128)
        if cv2.countNonZero(img)/img.size < 0.5:
            img = cv2.bitwise_not(img)
        templ_condition_counts.append(img)

    # 一部のテンプレート画像はPokemonクラスの初期化後、init()メソッドで読み込む
    templ_Ttypes = {}
    templ_ailments = {}
    templ_conditions = {}
    conditions, limited_conditions, countable_conditions = [], [], []

    def init():
        os.makedirs('log/battle/', exist_ok=True)

        # nxbt設定
        if is_linux:
            print('nxbtを接続中...')
            Pokebot.nx = nxbt.Nxbt()
            Pokebot.nxid = Pokebot.nx.create_controller(
                nxbt.PRO_CONTROLLER,
                reconnect_address=Pokebot.nx.get_switch_addresses(),
            )
            Pokebot.nx.wait_for_connection(Pokebot.nxid)

        # 遅延設定の読み込み
        if os.path.isfile('log/latency.log'):
            with open('log/latency.log', encoding='utf-8') as fin:
                lines = fin.readlines()
                if len(lines) == 2:
                    Pokebot.CAPTURE_TIME = float(lines[0].split()[1])
                    Pokebot.TRANS_CAPTURE_TIME = float(lines[1].split()[1])
                    print(f'画面遷移なしの遅延: {Pokebot.CAPTURE_TIME}')
                    print(f'画面遷移ありの遅延: {Pokebot.TRANS_CAPTURE_TIME}')

        # テンプレート画像の読み込み
        for t in Pokemon.type_file_code:
            img = BGR2BIN(cv2.imread(f'data/terastal/{Pokemon.type_file_code[t]}.png'), threshold=230, bitwise_not=True)
            Pokebot.templ_Ttypes[t] = img[24:-26, 20:-22]
        
        for s in Pokemon.ailments:
            Pokebot.templ_ailments[s] = (BGR2BIN(cv2.imread(f'data/screen/{s}.png'), threshold=200, bitwise_not=True))

        Pokebot.conditions = ['auroraveil'] + list(Battle().condition.keys()) + list(Pokemon().condition.keys())
        Pokebot.limited_conditions = ['aurora_veil'] + [
            'ame_mamire','encore','healblock','kanashibari','jigokuzuki','chohatsu','magnetrise','nemuke',
            'sunny','rainy','snow','sandstorm','elecfield','glassfield','psycofield','mistfield',
            'gravity','trickroom','oikaze','lightwall','reflector','safeguard','whitemist',
        ]
        Pokebot.countable_conditions = ['stock','makibishi','dokubishi']

        for s in Pokebot.conditions:
            img = BGR2BIN(cv2.imread(f'data/condition/{s}.png'), threshold=128)
            if cv2.countNonZero(img)/img.size < 0.5:
                img = cv2.bitwise_not(img)
            Pokebot.templ_conditions[s] = img
        
        Pokebot.is_init = True

    def __init__(self):
        if not Pokebot.is_init:
            Pokebot.init()
        
        super().__init__()
        self.party = [[], []] # [自分のPT, 相手のPT]
        self.t0 = time.time()
        self.process_buffer = []
        self.reset_game()

    def selection_command(self, player):
        commands = list(range(20 + len(self.party[player])))
        random.shuffle(commands)
        return commands[:3]
    
    def reset_game(self):
        self.start_time = time.time()
        super().reset_game()
        self.turn = 0
        self.selection_finished = False
        self.screen_record = []

        # 実戦では相手の観測値と真値は同一
        self.observed[1] = self.selected[1]

    def capture(self, filename=''):
        if is_linux or filename:
            cap.read() # バッファ対策
            _, self.img = cap.read()
            if filename:
                cv2.imwrite(filename, self.img)
            
    def set_image(self, filename):
        self.img = cv2.imread(filename)

    def press_button(self, button, n=1, interval=0.1, post_sleep=0.1):
        if not is_linux:
            return
        macro = ''
        for i in range(n):
            macro += f'{button} 0.1s\n'
            if i < n-1 and interval:
                macro += f'{interval}s\n'
        if post_sleep:
            macro += f'{post_sleep}s\n'
        if macro:
            macro_id = self.nx.macro(self.nxid, macro, block=False)
            while macro_id not in self.nx.state[self.nxid]['finished_macros']:
                time.sleep(0.01)

    def game_time(self):
        elapsed_time = time.time()-self.start_time
        return 20*60 - elapsed_time
    
    def thinking_time(self):
        match self.phase:
            case 'selection':
                return 90 - self.selection_command_time - (time.time()-self.t0)
            case 'battle':
                return 45 - self.battle_command_time - (time.time()-self.t0)
            case 'change':
                return 90 - self.change_command_time - (time.time()-self.t0)

    def overwrite_condition(self, player: int, condition: dict):
        """{player}の場とポケモンの状態を上書きする"""
        p = self.pokemon[player]

        # オーロラベールを両壁に書き換える
        if 'auroraveil' in condition:
            condition['reflector'] = condition['lightwall'] = condition['auroraveil']
            del condition['auroraveil']

        # 引数の条件にない項目をリセット
        for s in self.condition:
            if s not in condition:
                self.condition[s] = [0, 0] if type(self.condition[s]) == list else 0

        for s in p.condition:
            if s not in condition:
                p.condition[s] = 0

        for s in condition:
            # 場の状態を更新
            if s in self.condition:
                if s in list(self.condition.keys())[:10]:
                    self.condition[s] = condition[s]
                elif s == 'wish':
                    self.condition[s] = max(1, self.condition[s].real - 1) + 1j * self.condition[s].imag
                else:
                    self.condition[s][player] = condition[s]

            # ポケモンの状態を更新
            elif s in p.condition:
                if s == 'badpoison':
                    p.condition[s] += 1
                elif s in ['confusion','bind']:
                    p.condition[s] = max(1, p.condition[s] - 1) + 1j * p.condition[s].imag
                else:
                    p.condition[s] = condition[s]

    # cmd = 0~5 -> PTのcmd番目のポケモンを選出
    def input_selection_command(self, cmd_list):
        print(f'{cmd_list} 番目のポケモンを選出')
        
        for cmd in cmd_list + [6]: # [6]: 決定ボタン
            while True:
                pos = self.selection_cursor_position()
                if pos == cmd:
                    break
                n = cmd - pos
                button = 'DPAD_DOWN' if n > 0 else 'DPAD_UP'
                self.press_button(button, n=abs(n), post_sleep=self.CAPTURE_TIME)
                if not self.feedback_input:
                    break
                if self.read_phase() != 'selection':
                    warnings.warn('コマンド入力を完了できませんでした')
                    self.selected[0] = [deepcopy(p) for p in self.party[0][:3]]
                    return
            
            self.press_button('A', n=2, interval=self.PRESS_INTERVAL)
        
        self.selected[0] = [deepcopy(self.party[0][i]) for i in cmd_list[:-1]]

    # cmd = 0~3 -> cmd番目の技を選択
    # cmd = 10~13 -> テラスタルして(cmd-4)番目の技を選択
    # cmd = 20~25 -> (cmd-10)番目に選出したポケモンに交代
    def input_battle_command(self, cmd):
        print(f'コマンド {cmd}')

        # 技
        if cmd < 20 or cmd == 30:
            # 技選択画面に移動
            while True:
                if (pos := self.battle_cursor_position()) == 0:
                    break
                self.press_button('DPAD_UP', n=pos, post_sleep=self.CAPTURE_TIME)
                if not self.feedback_input:
                    break
                
            self.press_button('A', post_sleep=self.TRANS_CAPTURE_TIME+self.ADDITIONAL_TIME)

            # PPを取得
            for i in range(len(self.pokemon[0].pp)):
                pp = self.read_pp(idx=i, capture=(i==0))
                # 0の場合は読み直す
                if pp == 0 and pp != self.pokemon[0].pp[i]:
                    pp = self.read_pp(idx=i, capture=True)
                self.pokemon[0].pp[i] = pp

            print(f'\tPP {self.pokemon[0].pp}')

            if self.pokemon[0].pp[cmd%10] == 0:
                warnings.warn(f'{self.pokemon[0].moves[cmd%10]}のPPが不足しています')
                return False

            # テラスタル
            if cmd >= 10:
                self.press_button('R')

            # カーソル移動
            while True:
                if (pos := self.move_cursor_position()) == cmd%10:
                    break
                dpos = cmd%10 - pos
                button = 'DPAD_DOWN' if dpos > 0 else 'DPAD_UP'
                self.press_button(button, n=abs(dpos), post_sleep=self.CAPTURE_TIME)
                if not self.feedback_input:
                    break
                if self.read_phase() != 'battle':
                    return False

            # 技を選択
            self.press_button('A')

        # 交代
        elif cmd in range(20,26):
            cmd -= 20

            # 交代画面に移動
            print(f'{self.selected[0][cmd].name}に交代')
            while True:
                if (pos := self.battle_cursor_position()) == 1:
                    break
                dpos = 1 - pos
                button = 'DPAD_DOWN' if dpos > 0 else 'DPAD_UP'
                self.press_button(button, n=abs(dpos), post_sleep=self.CAPTURE_TIME)
                if not self.feedback_input:
                    break
                if self.read_phase() != 'battle':
                    return False

            self.press_button('A', post_sleep=0.5)

            # カーソル移動
            self.press_button('DPAD_DOWN', post_sleep=self.CAPTURE_TIME)
            for i in range(len(self.selected[0])-2):
                if self.read_party_condition() == 'alive':
                    display_name = self.read_party_display_name(i+1)
                    if display_name == self.selected[0][cmd].display_name:
                        break
                self.press_button('DPAD_DOWN', post_sleep=self.CAPTURE_TIME)
                if self.feedback_input and self.read_phase() != 'change':
                    return False

            # 交代先を選択
            self.press_button('A', n=2, interval=self.PRESS_INTERVAL)

        else:
            warnings.warn(f'コマンド{cmd}が不適切です')
            return False

        return True

    # cmd = 20~25 -> (cmd-20)番目に選出したポケモンに交代
    def input_change_command(self, cmd):
        if cmd not in self.available_commands(player=0, phase=self.phase):
            if cmd not in range(len(self.selected[0])):
                warnings.warn(f'コマンド{cmd}が不適切です')
            else:
                warnings.warn(f'{self.selected[0][cmd].name}に交代できません')
            return False

        cmd -= 20
        print(f'{self.selected[0][cmd].name}に交代')
        if self.is_change_window():
            self.press_button('DPAD_DOWN', post_sleep=self.CAPTURE_TIME)
            for i in range(len(self.selected[0])-2):
                if self.read_party_display_name(i+1) == self.selected[0][cmd].display_name:
                    break
                self.press_button('DPAD_DOWN', post_sleep=self.CAPTURE_TIME)
            self.press_button('A', n=2, interval=self.PRESS_INTERVAL)       

        return True
    
    # 盤面情報を収集
    def read_battle_situlation(self):
        self.press_button('Y', post_sleep=self.TRANS_CAPTURE_TIME)

        # 相手にテラスタル権があれば、テラスタルしているか確認
        Ttype = self.read_enemy_terastal() if self.can_terastal(player=1) else ''

        # 自分の盤面情報を取得
        if not 'player0' in self.screen_record:
            print('自分の盤面')
            self.press_button('A', post_sleep=self.TRANS_CAPTURE_TIME+self.ADDITIONAL_TIME)

            if not self.is_condition_window():
                warnings.warn('画面が不適切です')
                return False
            
            # 場のポケモンを取得
            display_name = self.read_display_name(player=0, capture=False)
            if self.pokemon[0] is None or display_name != self.pokemon[0].display_name:
                self.change_pokemon(
                    player=0,
                    idx=Pokemon.index(self.selected[0], display_name=display_name),
                    landing=False,
                )

            self.pokemon[0].hp = max(1, min(self.read_hp(capture=False), self.pokemon[0].status[0]))
            self.pokemon[0].ailment = self.read_ailment(capture=False)
            self.pokemon[0].rank[1:] = self.read_rank(capture=False)
            self.overwrite_condition(player=0, condition=self.read_condition(capture=False))

            if (item := self.read_item(capture=False)) != self.pokemon[0].item:
                if item:
                    self.pokemon[0].item = item
                else:
                    self.pokemon[0].item, self.pokemon[0].lost_item = '', self.pokemon[0].item

                # こだわり解除
                self.pokemon[0].fixed_move = ''

            # 画面認識が完了したことを記録
            self.screen_record.append('player0')
        else:
            self.press_button('A', post_sleep=self.PRESS_INTERVAL)

        # 相手の盤面情報を取得
        enemy_changed = False
        if not 'player1' in self.screen_record:
            print('相手の盤面')
            self.press_button('R', post_sleep=self.TRANS_CAPTURE_TIME)

            if not self.is_condition_window():
                warnings.warn('画面が不適切です')
                return False
            
            # 場のポケモンを取得
            display_name = self.read_display_name(player=1, capture=False)

            if self.vs_NPC:
                self.pokemon[1] = Pokemon(Pokemon.zukan_name[display_name][0], use_template=False)
                self.pokemon[1].level = 80
                self.selected[1].clear()
                self.selected[1].append(self.pokemon[1])
                self.selected[1][-1].speed_range = [0, 999]
            
            elif self.pokemon[1] is None or display_name != self.pokemon[1].display_name:
                enemy_changed = True

                # 初見なら選出に追加
                if display_name not in [p.display_name for p in self.selected[1]]:
                    p = deepcopy(Pokemon.find(self.party[1], display_name=display_name))

                    # フォルムを識別
                    if (name := self.read_form(display_name, capture=False)):
                        p.name = name

                    self.selected[1].append(p)
                    self.selected[1][-1].speed_range = [0, 999]

                    print(f'\t相手の選出 {[p.name for p in self.selected[1]]}')

                # 交代
                self.change_pokemon(
                    player=1,
                    idx=Pokemon.index(self.selected[1], display_name=display_name),
                    landing=False,
                )
                
            # 相手のテラスタルを取得
            if Ttype:
                self.pokemon[1].Ttype = Ttype
                self.pokemon[1].use_terastal()

            self.pokemon[1].hp_ratio = self.read_hp_ratio(capture=False)
            self.pokemon[1].ailment = self.read_ailment(capture=False)
            self.pokemon[1].rank[1:] = self.read_rank(capture=False)
            self.overwrite_condition(player=1, condition=self.read_condition(capture=False))

            # 画面認識が完了したことを記録
            self.screen_record.append('player1')

        # コマンド選択画面に戻る
        while True:
            self.press_button('B', n=2, interval=0.5, post_sleep=self.TRANS_CAPTURE_TIME)
            if self.is_battle_window() or not self.feedback_input:
                break
        
        # 相手が交代していれば、相手の控えが瀕死かどうか確認
        if enemy_changed:
            self.press_button('PLUS', post_sleep=self.TRANS_CAPTURE_TIME)
            self.read_enemy_death()
            self.press_button('B', post_sleep=self.PRESS_INTERVAL)

        return True

    def is_battle_window(self, capture=True):
        if capture:
            self.capture()
        img1 = BGR2BIN(self.img[997:1039, 827:869], threshold=200, bitwise_not=True)
        return template_match_score(img1, self.templ_battle) > 0.95 # 黄色点滅時にも読み取れるように閾値を下げている

    def is_change_window(self, capture=True):
        if capture:
            self.capture()
        img1 = BGR2BIN(self.img[140:200, 770:860], threshold=150, bitwise_not=True)
        return template_match_score(img1, self.templ_change) > 0.99

    def is_selection_window(self, capture=True):       
        if capture:
            self.capture()
        img1 = BGR2BIN(self.img[14:64, 856:906], threshold=100, bitwise_not=True)
        return template_match_score(img1, self.templ_selection) > 0.99

    def is_standby_window(self, capture=True):
        if capture:
            self.capture()
        img1 = BGR2BIN(self.img[10:70, 28:88], threshold=100, bitwise_not=True)
        return template_match_score(img1, self.templ_standby) > 0.99

    def is_condition_window(self, capture=True):
        if capture:
            self.capture()
        img1 = BGR2BIN(self.img[76:132, 1112:1372], threshold=200, bitwise_not=True)
        return template_match_score(img1, self.templ_condition_window) > 0.99

    # 0~5: ポケモン, 6: 完了
    def selection_cursor_position(self, capture=True):
        if capture:
            self.capture()
        for i in range(6):
            img1 = cv2.cvtColor(self.img[200+116*i:250+116*i, 500:550], cv2.COLOR_BGR2GRAY)
            #cv2.imwrite(f'log/{i}.png', img1)
            if img1[0,0] > 150:
                return i
        return 6

    # オンライン -> 0: たたかう, 1:ポケモン, 2:にげる
    # オフライン -> 0: たたかう, 1:ポケモン, 2:バッグ, 3:にげる
    def battle_cursor_position(self, capture=True):
        if capture:
            self.capture()
        y0 = 700 if self.vs_NPC else 788
        for i in range(4):
            img1 = cv2.cvtColor(self.img[y0+88*i:y0+88*i+70, 1800:1850], cv2.COLOR_BGR2GRAY)
            if img1[0,0] > 150:
                return i
        return 0

    def move_cursor_position(self, capture=True):
        if capture:
            self.capture()
        for i in range(4):
            img1 = cv2.cvtColor(self.img[680+112*i:700+112*i, 1420:1470], cv2.COLOR_BGR2GRAY)
            #cv2.imwrite(f'log/trim_{i}.png', img1)
            if img1[0,0] > 150:
                return i
        return 0

    def read_pp(self, idx, capture=True):
        if capture:
            self.capture()
        for thr in [200, 150, 120]:
            img1 = BGR2BIN(self.img[660+112*idx:700+112*idx, 1755:1800], threshold=thr, bitwise_not=True)
            #cv2.imwrite(f'log/trim_{idx}.png', img1)
            s = OCR(img1, lang='num', log_dir='log/ocr/pp/')
            if s and not s[-1].isdigit():
                s = s[:-1]
            if s.isdigit():
                return int(s)
        return 0
    
    def read_phase(self, capture=True):
        # バトル画面の判定
        if self.is_battle_window(capture=capture):
            self.phase = 'battle'
            return self.phase

        # 交代画面の判定
        if self.is_change_window(capture=False):
            self.phase = 'change'
            return self.phase

        # 選出画面の判定
        if self.is_selection_window(capture=False):
            self.phase = 'selection'
            return self.phase

        # 待機画面の判定
        if self.is_standby_window(capture=False):
            self.phase = 'standby'
            return self.phase

        self.phase = None
        return self.phase

    def read_party_condition(self, capture=True):
        if capture:
            self.capture()
        img1 = self.img[140:200, 1060:1300]
        img1 = BGR2BIN(self.img[140:200, 1060:1260], threshold=150, bitwise_not=True)
        for s in self.templ_alives:
            if template_match_score(img1, self.templ_alives[s]) > 0.99:
                return s

    def read_party_display_name(self, i, capture=True):
        if capture:
            self.capture()
        img1 = BGR2BIN(self.img[171+126*i:212+126*i, 94:300], threshold=100)
        #cv2.imwrite(f'log/trim_{i}.png', img1)
        candidates = sum([Pokemon.foreign_display_names[p.display_name] for p in self.selected[0]], [])
        s = OCR(img1, candidates=candidates, lang='all', log_dir='log/ocr/change_name/')
        return Pokemon.japanese_display_name[s]

    def read_party_hp(self, index, capture=True):
        if capture:
            self.capture()
        img1 = BGR2BIN(self.img[232+126*index:268+126*index, 110:298], threshold=200, bitwise_not=True)
        s = OCR(img1, lang='eng')
        s = s[:s.find('/')]
        s = s.replace('T', '7')
        hp = 0 if not s.isdigit() else int(s)
        return hp

    def read_enemy_party(self, capture=True):
        print('相手のパーティ')
        if capture:
            self.capture()
        self.party[1] = []        
        trims = []
        # アイコン
        for i in range(6):
            y0 = 236+101*i-(i<2)*2
            trims.append(rect_trim(self.img[y0:(y0+94), 1246:(1246+94)], threshold=200))
            trims[i] = cv2.cvtColor(trims[i], cv2.COLOR_BGR2GRAY)

        candidates = list(Pokemon.home.keys())

        scores, names = [0]*6, ['']*6
        for filename in glob.glob('data/template/*.png'):
            code = os.path.splitext(os.path.basename(filename))[0]
            s = Pokemon.template_file_code[code]
            if s not in candidates:
                continue
            template = cv2.cvtColor(cv2.imread(filename), cv2.COLOR_BGR2GRAY)

            for i in range(6):
                w, h = trims[i].shape[1], trims[i].shape[0]
                if w<2 or h<2:
                    break
                ht = int(w*template.shape[0]/template.shape[1])
                if abs(ht-h) > 3:
                    continue
                score = template_match_score(trims[i], cv2.resize(template, (w, ht)))
                if scores[i] < score:
                    scores[i] = score
                    names[i] = s
            
        # 相手のパーティに追加
        for i,name in enumerate(names):
            # 名前を修正
            if 'イルカマン' in name:
                name = 'イルカマン(ナイーブ)'
            self.party[1].append(Pokemon(name, use_template=False))
            print(f'\t{i}: {name}')

        # 性別
        '''
        for i in range(6):
            y0 = 250+101*i
            img1 = self.img[y0:(y0+94), 1400:(1500)]
            cv2.imwrite(f'log/trim_{i}.png', img1)
            img1 = cv2.cvtColor(trims[i], cv2.COLOR_BGR2GRAY)       
        '''

    def read_enemy_terastal(self, capture=True):
        if capture:
            self.capture()
        Ttype = ''
        img1 = BGR2BIN(self.img[200:282, 810:882], threshold=230, bitwise_not=True)
        img1 = img1[24:-26, 20:-22]
        # 有色 = テラスタルしている
        if cv2.minMaxLoc(img1)[0] == 0:
            max_score, Ttype = 0, ''
            for t in self.templ_Ttypes:
                score = template_match_score(img1, self.templ_Ttypes[t])
                if max_score < score:
                    max_score = score
                    Ttype = t
        print(f'\t相手のテラスタル {Ttype}')
        return Ttype

    def read_display_name(self, player=0, capture=True):
        if capture:
            self.capture()
        img1 = BGR2BIN(self.img[80:130, 160:450], threshold=200, bitwise_not=True)
        candidates = []
        if self.vs_NPC and player == 1:
            candidates = list(Pokemon.zukan_name.keys())
        else:
            for p in self.party[player]:
                candidates += Pokemon.foreign_display_names[p.display_name]

        s = OCR(img1, lang='all', candidates=candidates, log_dir='log/ocr/display_name/')
        display_name = Pokemon.japanese_display_name[s]
        print(f'\t名前 {display_name}')
        return display_name

    def read_hp(self, capture=True):
        if capture:
            self.capture()
        img1 = BGR2BIN(self.img[475:515, 210:293], threshold=200, bitwise_not=False)
        s = OCR(img1, lang='num', log_dir='log/ocr/hp/')
        if s and not s[-1].isdigit():
            s = s[:-1]
        hp = 1
        if s.isdigit():
            hp = max(1, int(s))
            print(f'\tHP {hp}')
        else:
            warnings.warn(f'HP{s}が数字ではありません')
        return hp

    def read_hp_ratio(self, capture=True):
        if capture:
            self.capture()
        dy, dx = 46, 242
        img1 = BGR2BIN(self.img[472:(472+dy), 179:(179+dx)], threshold=100, bitwise_not=True)
        count = 0
        for i in range(dx):
            if img1.data[int(dy/2),i] == 0:
                count += 1
        rhp = max(0.001, min(1, count/240))
        print(f'\tHP {int(rhp*100)}%')
        return rhp

    def read_item(self, capture=True):
        if capture:
            self.capture()
        img1 = BGR2BIN(self.img[350:395, 470:760], threshold=230, bitwise_not=True)
        #cv2.imwrite(f'log/trim.png', img1)
        return OCR(img1, candidates=list(Pokemon.items.keys())+[''], log_dir='log/ocr/item/')

    def read_rank(self, capture=True):
        if capture:
            self.capture()

        dx, dy, y1 = 40, 60, 15
        ranks = [0]*7
        
        for j in range(7):
            y = 595 + dy*j + y1*(j>4)

            for i in range(6):
                x = 500 + dx*i
                if self.img[y-2, x][1] > 190: # 緑
                    ranks[j] += 1
                elif self.img[y+2, x][1] < 80: # 赤
                    ranks[j] -= 1
                else:
                    break

        if any(ranks):
            print('\t能力ランク ' + ' '.join([s + ('+' if v > 0 else '') + \
            str(v) for s,v in zip(Pokemon.status_label[1:], ranks) if v]))
        
        return ranks

    def read_ailment(self, capture=True):
        if capture:
            self.capture()

        #cv2.imwrite('log/trim.png',self.img[430:460, 270:360])
        img1 = BGR2BIN(self.img[430:460, 270:360], threshold=200, bitwise_not=True)
        result = ''
        for ailment in self.templ_ailments:
            if template_match_score(img1, self.templ_ailments[ailment]) > 0.99:
                result = ailment
                print(f'\t状態異常 {result}')
                break
        return result

    def read_condition(self, capture=True):
        if capture:
            self.capture()

        dy = 86
        condition = {}

        for i in range(6):
            img1 = BGR2BIN(self.img[188+dy*i:232+dy*i, 1190:1450], threshold=128)
            if cv2.minMaxLoc(img1)[0]:
                break
            if cv2.countNonZero(img1)/img1.size < 0.5:
                img1 = cv2.bitwise_not(img1)

            for t in self.templ_conditions:
                if template_match_score(img1, self.templ_conditions[t]) > 0.99:
                    if t in self.limited_conditions:
                        # 残りターン数を取得
                        img2 = BGR2BIN(self.img[188+dy*i:232+dy*i, 1710:1733], threshold=128)
                        if cv2.countNonZero(img2)/img2.size < 0.5:
                            img2 = cv2.bitwise_not(img2)
                        for j in range(len(self.templ_condition_turns)):
                            if template_match_score(img2, self.templ_condition_turns[j]) > 0.99:
                                condition[t] = j+1
                                break

                    elif t in self.countable_conditions:
                        # カウントを取得
                        img2 = BGR2BIN(self.img[188+dy*i:232+dy*i, 1738:1766], threshold=128)
                        if cv2.countNonZero(img2)/img2.size < 0.5:
                            img2 = cv2.bitwise_not(img2)
                        for j in range(len(self.templ_condition_counts)):
                            if template_match_score(img2, self.templ_condition_counts[j]) > 0.99:
                                condition[t] = j+1
                                break

                    elif t == 'horobi':
                        # 滅びカウントを取得
                        img2 = BGR2BIN(self.img[188+dy*i:232+dy*i, 1725:1755], threshold=128)
                        if cv2.countNonZero(img2)/img2.size < 0.5:
                            img2 = cv2.bitwise_not(img2)
                        for j in range(len(self.templ_condition_horobis)):
                            if template_match_score(img2, self.templ_condition_horobis[j]) > 0.99:
                                condition[t] = j+1
                                break
                    else:
                        condition[t] = 1
                    break
        
        if condition:
            print(f'\t{condition}')
        
        return condition

    def read_enemy_death(self, capture=True):
        if capture:
            self.capture()

        dy = 102
        for i,p in enumerate(self.party[1]):
            img1 = BGR2BIN(self.img[280+dy*i:302+dy*i, 1314:1334], threshold=128)
            if template_match_score(img1, self.templ_dead_enemy) > 0.99:
                p1 = Pokemon.find(self.selected[1], display_name=p.display_name)

                # 出オチした相手ポケモンは選出に追加する
                if p1 is None:
                    p1 = deepcopy(Pokemon.find(self.party[1], display_name=p.display_name))
                    self.selected[1].append(p1)

                p1.hp = 0
                print(f'{p1.display_name} 瀕死')

    def dump(self):
        dict = {
            'index': [],            # 場のポケモンの選出番号
            'selected':[[], []]
        }
        for i in range(2):
            dict['index'].append(self.selected[i].index(self.pokemon[i]))
            for p in self.selected[i]:
                dict['selected'][i].append(vars(p))

        dict['game_time'] = self.game_time()
        dict['command'] = self.command
        dict['stellar'] = self.stellar
        dict['condition'] = self.condition
        dict['was_valid'] = self.was_valid

        return json.dumps(dict, ensure_ascii=False)        

    def dump_party(self, player=0):
        result = {}
        for i,p in enumerate(self.party[player]):
            result[str(i)] = {
                'name': p.name,
                'sex': p.sex,
                'level': p.level,
                'nature': p.nature,
                'ability': p.ability,
                'item': p.item,
                'Ttype': p.Ttype,
                'moves': p.moves,
                'indiv': p.indiv,
                'effort': p.effort,
            }
        return json.dumps(result, ensure_ascii=False)

    def load_party(self):
        print('パーティ読み込み中...')
        self.party[0].clear()
        with open('log/party.log', encoding='utf-8') as fin:
            dict = json.load(fin)

            for s in dict:
                self.party[0].append(Pokemon())
                self.party[0][-1].name = dict[s]['name']
                self.party[0][-1].sex = dict[s]['sex']
                self.party[0][-1].level = dict[s]['level'] if self.vs_NPC else 50
                self.party[0][-1].nature = dict[s]['nature']
                self.party[0][-1].ability = dict[s]['ability']
                self.party[0][-1].item = dict[s]['item']
                self.party[0][-1].Ttype = dict[s]['Ttype']
                self.party[0][-1].moves = dict[s]['moves']
                self.party[0][-1].indiv = dict[s]['indiv']
                self.party[0][-1].effort = dict[s]['effort']
                self.party[0][-1].show()

    def save_party(self):
        print('パーティは "log/party.log" に保存されます')
        template = BGR2BIN(cv2.imread('data/screen/judge.png'), threshold=128)
        self.party[0] = []
        for i in range(6):
            self.capture()
            img1 = BGR2BIN(self.img[1020:1060, 1372:1482], threshold=128)
            if template_match_score(img1, template) < 0.95:
                warnings.warn('画面が不適切です')
                if i==0:
                    return
                else:
                    break
            self.party[0].append(Pokemon())
            self.read_box_pokemon(i)
            self.press_button('DPAD_DOWN', post_sleep=self.TRANS_CAPTURE_TIME)
            if not is_linux:
                break

        with open('log/party.log', 'w', encoding='utf-8') as fout:
            fout.write(self.dump_party(player=0))

        self.press_button('DPAD_UP', n=len(self.party[0]))

    def read_box_pokemon(self, ind):
        self.capture()

        # 特性：フォルムの識別に使うため先に読み込む
        img1 = BGR2BIN(self.img[580:620, 1455:1785], threshold=180, bitwise_not=True)
        ability = OCR(img1, candidates=Pokemon.abilities, log_dir='log/ocr/box_ability/')

        # 名前
        img1 = BGR2BIN(self.img[90:130, 1420:1620], threshold=180, bitwise_not=True)
        display_name = OCR(img1, candidates=list(Pokemon.zukan_name.keys()), log_dir='log/ocr/box_name/')
        name = Pokemon.zukan_name[display_name][0]

        # フォルム識別
        if display_name in Pokemon.form_diff:
            for s in Pokemon.zukan_name[display_name]:
                # タイプで識別
                if Pokemon.form_diff[display_name] == 'type':
                    types = []
                    for t in range(2):
                        img1 = BGR2BIN(self.img[150:190, 1335+200*t:1480+200*t], threshold=230)
                        type = OCR(img1, candidates=list(Pokemon.type_id.keys()), log_dir='log/ocr/box_type/')
                        types.append(type)
                    if types == Pokemon.zukan[s]['type'] or [types[1],types[0]] == Pokemon.zukan[s]['type']:
                        name = s
                        break
                # 特性で識別
                elif Pokemon.form_diff[display_name] == 'ability' and ability in Pokemon.zukan[s]['ability']:
                    name = s
                    break

        self.party[0][ind].name = name
        print(f'{ind} {name}')

        # 性格
        x = [1590, 1689, 1689, 1491, 1491, 1590]
        y = [267, 321, 437, 321, 437, 491]
        nature_correction = [1]*6
        for j in range(6):
            if self.img[y[j], x[j]][2] < 50:
                nature_correction[j] = 0.9
            elif self.img[y[j], x[j]][1] < 80:
                nature_correction[j] = 1.1
        for nature in Pokemon.nature_corrections:
            if nature_correction == Pokemon.nature_corrections[nature]:
                self.party[0][ind].nature = nature
                break
        print(f'\t性格 {self.party[0][ind].nature}')

        # 特性
        if ability not in Pokemon.zukan[name]['ability']:
            if name in Pokemon.home:
                ability = Pokemon.home[name]['ability'][0][0]
            else:
                ability = Pokemon.zukan[name]['ability'][0]
        self.party[0][ind].org_ability = ability
        print(f'\t特性 {self.party[0][ind].ability}')

        # もちもの
        img1 = BGR2BIN(self.img[635:685, 1455:1785], threshold=180, bitwise_not=True)
        self.party[0][ind].item = OCR(img1, candidates=list(Pokemon.items.keys())+[''], log_dir='log/ocr/box_item/')
        print(f'\tアイテム {self.party[0][ind].item}')

        # テラスタイプ
        x0 = 1535+200*(len(self.party[0][ind].types)-1)
        img1 = BGR2BIN(self.img[154:186, x0:x0+145], threshold=240, bitwise_not=True)
        self.party[0][ind].Ttype = OCR(img1, candidates=list(Pokemon.type_id.keys()), log_dir='log/ocr/box_Ttype/')
        print(f'\tテラスタイプ {self.party[0][ind].Ttype}')

        # 技
        moves = ['']*4
        for j in range(4):
            img1 = BGR2BIN(self.img[700+60*j:750+60*j, 1320:1570], threshold=180, bitwise_not=True)
            moves[j] = OCR(img1, candidates=list(Pokemon.all_moves.keys())+[''], log_dir='log/ocr/box_move/')
        self.party[0][ind].moves = moves
        print(f'\t技 {self.party[0][ind].moves}')

        # レベル
        img1 = BGR2BIN(self.img[25:55, 1775:1830], threshold=180, bitwise_not=True)
        self.party[0][ind].level = int(OCR(img1, log_dir='log/ocr/box_level/', lang='num').replace('.', ''))
        print(f'\tレベル {self.party[0][ind].level}')

        # 性別
        if self.img[40, 1855][0] > 180:
            self.party[0][ind].sex = Pokemon.MALE
        elif self.img[40, 1855][1] < 100:
            self.party[0][ind].sex = Pokemon.FEMALE
        else:
            self.party[0][ind].sex = Pokemon.NONSEXUAL
        print(f'\tSex: {self.party[0][ind].sex}')

        # ステータス
        x = [1585, 1710, 1710, 1320, 1320, 1585]
        y = [215, 330, 440, 330, 440, 512]
        status = [0]*6
        for j in range(6):
            img1 = BGR2BIN(self.img[y[j]:y[j]+45, x[j]:x[j]+155], threshold=180, bitwise_not=True)
            s = OCR(img1, lang=('eng' if j==0 else 'num'))
            if j==0:
                s = s[s.find('/')+1:]
            status[j] = int(s)
        self.party[0][ind].status = status
        print(f'\tステータス {self.party[0][ind].status}')
        print(f'\t努力値 {self.party[0][ind].effort}')

        # ザシアン・ザマゼンタの識別
        if (self.party[0][ind].name == 'ザシアン(れきせん)' and self.party[0][ind].item == 'くちたけん') or \
            (self.party[0][ind].name == 'ザマゼンタ(れきせん)' and self.party[0][ind].item == 'くちたたて'):
            self.party[0][ind].change_form(self.party[0][ind].name[:-5] + self.party[0][ind].item[-2:] + 'のおう)')
            print(f'\tフォルム: {self.party[0][ind].name}')

    def read_buffer(self):
        new_buffer = []
        move_order = []

        for i,dict in enumerate(self.process_buffer):
            # 対象のプレイヤー
            player = dict['player']
            
            # 対象のポケモンの表示名
            candidates = sum([Pokemon.foreign_display_names[p.display_name] for p in self.observed[player]], [])
            dict['display_name'] = most_similar_element(candidates, dict['display_name'])

            for selected in [self.observed[player], self.selected[player]]:
                # 対象のポケモン
                p = Pokemon.find(selected, display_name=dict['display_name'])

                # 該当するポケモンがいない場合、次回に持ち越す
                if p is None:
                    new_buffer.append(dict)
                    break
                
                if 'ability' in dict:
                    p.ability = dict['ability']
                    if p.ability == 'ばけのかわ':
                        p.ability = 'ばけのかわ+'

                elif 'item' in dict:
                    p.item = dict['item']
                    if p.item == p.lost_item:
                        p.lost_item = ''
                    p.fixed_move = ''

                elif 'lost_item' in dict:
                    p.item, p.lost_item = '', dict['lost_item']
                    if p.lost_item == 'ブーストエナジー' and p.name == self.pokemon[player].name:
                        p.BE_activated = True
                    p.fixed_move = ''

                elif 'subst_broken' in dict:
                    p.sub_hp = 0

                elif 'type' in dict:
                    p.lost_types, p.added_types = p.types, [dict['type']]

                elif 'boost' in dict:
                    p.boost_index = dict['boost']

                elif 'move' in dict:
                    # ねごとなど、1ターンに2度わざの演出がある場合
                    if i > 1 and 'move' in self.process_buffer[i-1] and \
                        self.process_buffer[i-1]['player'] == player and \
                        self.process_buffer[i-1]['move'] in Pokemon.move_category['other_move']:
                        p.last_used_move = dict['move']

                    # 通常技
                    else:
                        p.last_pp_move = p.last_used_move = dict['move']
                        
                        # 相手の技を追加
                        if player == 1 and p.last_pp_move not in p.moves:
                            p.add_move(p.last_pp_move)
                        
                        # PPを減らす
                        # 技を使った次のターンに、場にプレッシャーのポケモンがいれば、PPが2減ったと仮定する
                        if p.last_pp_move in p.moves:
                            ind = p.moves.index(p.last_pp_move)
                            p.pp[ind] -= 2 if self.pokemon[not player].ability == 'プレッシャー' else 1

                            # 相手の行動をコマンドに置き換える
                            if player == 1:
                                self.command[1] = ind + 10*p.terastal

                        # 使われた技を記録
                        if not move_order or move_order[-1]['player'] != player:
                            move_order.append(dict)

                    self.was_valid[player] = dict['was_valid'] and dict['hit']
                    
                    # 技の効果を反映させる
                    if self.was_valid[player]:
                        match dict['move']:
                            case 'でんこうそうげき':
                                p.lost_types.append('でんき')
                            case 'もえつきる':
                                p.lost_types.append('ほのお')
                            case 'みがわり':
                                p.sub_hp = int(p.status[0]/4)
                            case 'しっぽきり':
                                if (p1 := Pokemon.find(selected, name=self.pokemon[player].name)):
                                    p1.sub_hp = int(p.status[0]/4)
                            case 'バトンタッチ':
                                if p.sub_hp and (p1 := Pokemon.find(selected, name=self.pokemon[player].name)):
                                    p1.sub_hp = p.sub_hp

                # 相手のobservedとselectedは同値のため中断
                if player == 1:
                    break

        # 次回に持ち越し
        self.process_buffer = new_buffer

        # わざ優先度が同じなら、素早さの大小関係を記録する
        if len(move_order) == 2 and move_order[0]['move_speed'] == move_order[1]['move_speed']:
            # 行動順 [先手, 後手]
            action_order = [dict['player'] for dict in move_order]

            # 相手の行動順
            e = action_order.index(1)

            # テキスト取得時点での、相手のS補正値
            r_speed = move_order[e]['eff_speed'] / move_order[e]['speed']
            
            p = Pokemon.find(self.selected[1], display_name=move_order[e]['display_name'])

            # 相手のSの上下限 = 自分のS / 相手のS補正値
            speed = int(move_order[not e]['speed'] / r_speed)

            # 相手が先手ならSの最小値を、後手なら最大値を更新する
            if e == 0:
                p.speed_range[e] = max(p.speed_range[e], speed)
            else:
                p.speed_range[e] = min(p.speed_range[e], speed)
            
            print(f'素早さ推定 {p.name} {p.speed_range[0]}~{p.speed_range[1]}')

    def read_form(self, display_name, capture=True):
        if display_name not in ['ウーラオス','ケンタロス','ザシアン','ザマゼンタ']:
            return ''
        
        if capture:
            self.capture()

        type = ['']*2
        dx = 210
        for i in range(2):
            img1 = BGR2BIN(self.img[170:210, 525+dx*i:665+dx*i], threshold=230, bitwise_not=True)
            if cv2.minMaxLoc(img1)[0] == 255:
                type[i] = ''
            else:
                type[i] = OCR(img1, candidates=list(Pokemon.type_id.keys()), log_dir='log/ocr/display_type/')
        for name in Pokemon.zukan_name[display_name]:
            zukan_type = Pokemon.zukan[name]['type'].copy()
            if len(zukan_type) == 1:
                zukan_type.append('')
            if zukan_type == type or zukan_type == [type[1],type[0]]:
                return name
        
        warnings.warn(f'\t{display_name}のフォルムを識別できませんでした')
        return ''

    def read_win_lose(self, capture=True):
        if capture:
            self.capture()
        img1 = BGR2BIN(self.img[940:1060, 400:750], threshold=140, bitwise_not=True)
        result = ''
        for s in self.templ_winlose:
            if template_match_score(img1, self.templ_winlose[s]) > 0.99:
                result = s
                print(f'ゲーム終了 {result}')
                break
        return result

    def trim(self):
        dy = 86
        for i in range(6):
            img1 = self.img[188+dy*i:232+dy*i, 1190:1450] # condition
            #img1 = self.img[188+dy*i:232+dy*i, 1710:1733] # turn
            #img1 = self.img[188+dy*i:232+dy*i, 1738:1766] # count
            #cv2.imwrite(f'log/trim_{i}.png', img1)
            img1 = BGR2BIN(img1, threshold=128, bitwise_not=True)
            if cv2.countNonZero(img1)/img1.size < 0.5:
                img1 = cv2.bitwise_not(img1)
            #cv2.imwrite(f'log/trim_{i}.png', img1)

    def read_ability_text(self, player, capture=True):
        if capture:
            self.capture()

        dx, dy = 1050, 44
        words = []

        # 行ごとに文字認識
        for i in range(2):
            img1 = self.img[498+dy*i:540+dy*i, 300+dx*player:600+dx*player]
            img1 = BGR2BIN(img1, threshold=250, bitwise_not=True)
            #cv2.imwrite(f'log/trim_{player}_{i}.png', img1)
            
            # 文字が含まれていなければ中断
            if 0 not in img1:
                return False
            
            s = OCR(img1, lang=('all' if i == 0 else 'jpn'))#, log_dir='log/ocr/ability_text/')
            words += s.split()

            # 形式が不適切なら中断
            if not words or words[0][-1] != 'の':
                return False

        # 形式が不適切なら中断
        if len(words) != 2:
            return False

        dict = {
            'player': player,
            'display_name': words[0][:-1],
            'ability': most_similar_element(Pokemon.abilities, words[1])
        }
        
        if dict not in self.process_buffer:
            self.process_buffer.append(dict)
            #print(words)
            return True
        else:
            return False

    def read_bottom_text(self, capture=True):
        if capture:
            self.capture()

        dy = 63
        words = []

        # 行ごとに文字認識
        for i in range(2):
            img1 = self.img[798+dy*i:842+dy*i, 285:1000]
            img1 = BGR2BIN(img1, threshold=250, bitwise_not=True)
            #cv2.imwrite(f'log/trim_{i}.png', img1)

            # 文字が含まれていなければ中断
            if 0 not in img1:
                return False

            s = OCR(img1, lang=('all' if i == 0 else 'jpn'))#, log_dir='log/ocr/bottom_text/')
            words += to_jpn_upper(s).split()

        # 形式が不適切なら中断
        if len(words) < 2 or 'ブースト' in words[0]:
            return False

        # 対NPC
        if self.vs_NPC and 'しかけて' in words[-1]:
            print('----------- 次の試合 -----------')
            self.reset_game()
            self.selected[0] = deepcopy(self.party[0])
            self.process_buffer.clear()
            return False

        # 対象のプレイヤー
        player = 0
        if '相手' in words[0] or 'あいて' in words[0]:
            player = 1
            words = words[1:]

        # わざ失敗
        if words[0] == 'しかし' or words[-1][:4] == 'ないよう':
            if self.process_buffer and 'move' in self.process_buffer[-1]:
                self.process_buffer[-1]['was_valid'] = False
                return True
            else:
                return False
        
        # わざ外し
        if words[1][1:4] == 'たらな':
            if self.process_buffer and 'move' in self.process_buffer[-1]:
                self.process_buffer[-1]['hit'] = False
                return True
            else:
                return False

        # 急所
        if words[0] in ['急所に','きゆうしよに']:
            if self.process_buffer and 'move' in self.process_buffer[-1]:
                self.process_buffer[-1]['critical'] = True
                return True
            else:
                return False

        dict = {'player': player, 'display_name': words[0][:-1]}

        # ひるみ
        if words[-1][:3] == 'だせな':
            dict['flinch'] = True

        # みがわり
        elif '代わり' in ''.join(words) or 'がわり' in ''.join(words):
            # みがわり解除
            if words[1][-1] == 'は':
                dict['subst_broken'] = True
            else:
                return False
        
        # はたきおとす
        elif words[-2][-1] == 'を' and words[-1][:2] == 'はた':
            dict['player'] = bool(not player)
            dict['display_name'] = words[1][:-1]
            if player == 0:
                dict['display_name'] = dict['display_name'].replace('相手の','').replace('あいての','')
            dict['lost_item'] = most_similar_element(list(Pokemon.items.keys()), words[2][:-1])

        # いのちのたま
        elif words[-1][:2] == '少し' or words[-1][:3] == 'すこし':
            dict['item'] = 'いのちのたま'

        elif words[-1][:2] in ['手に','てに']:
            # トリック
            dict['item'] = most_similar_element(list(Pokemon.items.keys()), words[1][:-1])

        # ふうせん破壊
        elif 'ふうせんが' in words[1]:
            dict['lost_item'] = 'ふうせん'
        
        # へんげんじざい
        elif words[-1][:2] == 'なつ':
            dict['type'] = most_similar_element(list(Pokemon.type_id.keys()), words[1][:-4])

        # しゅうかく
        elif words[-1][0] == '収' or words[-1][:3] == 'しゆう':
            dict['item'] = most_similar_element(list(Pokemon.items.keys()), words[1][:-1])
        
        # クォークチャージ
        elif words[-1][0] == '高' or words[-1][:3] == 'たかま':
            labels = Pokemon.status_label_hiragana + Pokemon.status_label_kanji
            s = most_similar_element(labels, words[1][:-1])
            dict['boost'] = labels.index(s)%5 + 1
        
        # 技・アイテム
        else:
            # 形式が不適切なら中断
            if words[0][-1] not in ['の','は'] or words[-1][1:3] == 'りだ':
                return False

            # 誤認する可能性のある候補をすべて含ませる
            candidates = list(Pokemon.all_moves.keys()) + list(Pokemon.items.keys()) + \
                list(Pokemon.ailments) + ['まひし'] + Pokemon.abilities + \
                Pokemon.status_label_hiragana + Pokemon.status_label_kanji + \
                ['守り', 'まもり']
            
            s = most_similar_element(candidates, words[1][:-1])

            if s in Pokemon.all_moves:
                dict['move'] = s
                dict['hit'] = True
                dict['critical'] = False
                dict['was_valid'] = True
                dict['speed'] = self.pokemon[player].status[5]
                dict['eff_speed'] = self.eff_speed(player)
                dict['move_speed'] = self.move_speed(player, s, random=False)
            elif s in Pokemon.items:
                if s in Pokemon.consumable_items:
                    dict['lost_item'] = s
                else:
                    dict['item'] = s

        if len(dict.keys()) > 2 and dict not in self.process_buffer:
            #print(words)
            #print(dict)
            self.process_buffer.append(dict)
            return True
        else:
            return False

    def main_loop(self, feedback_input=True, vs_NPC=False):
        self.feedback_input = feedback_input
        self.vs_NPC = bool(vs_NPC)
        print('対NPC' if self.vs_NPC else '対人戦')
        
        self.load_party()

        logfile = None

        # 対NPC戦の初期化
        if self.vs_NPC:
            self.selected[0] = deepcopy(self.party[0])
            self.press_button('B', n=6, post_sleep=1)

            filename = 'log/battle/npc.log'
            print(f'ログ出力 {filename}')
            logfile = open(filename, 'w', encoding='utf-8')
            logfile.write(self.dump_party(player=0) + '\n')

        while True:
            phase = self.read_phase()
            
            if phase is not None:
                # 対NPC戦でA連打による画面遷移への対策
                if self.vs_NPC:
                    self.press_button('B', n=4, post_sleep=1)
                    if self.read_phase() != phase:
                        continue

                print(f'=== Phase : {phase} ===')
                self.t0 = time.time()

            match phase:
                case 'standby':
                    self.press_button('A', post_sleep=0.5)

                case 'selection':
                    if self.selection_finished:
                        continue

                    # 時間計測開始
                    t0 = time.time()

                    # 試合をリセット
                    self.reset_game()
                    
                    if os.path.isdir('log/ocr/'):
                        shutil.rmtree('log/ocr/')
                        print("OCR履歴 'log/ocr/' を削除")

                    # 相手のパーティを読み込む
                    self.press_button('B', n=4)
                    self.read_enemy_party()
                    dt = time.time() - t0

                    # コマンドを取得
                    cmd = self.selection_command(player=0)

                    # コマンドを入力
                    t0 = time.time()
                    self.input_selection_command(cmd) 
                    dt += time.time() - t0
                    
                    # コマンド入力にかかった時間を記録
                    print(f'操作時間 {dt:.1f}')
                    self.selection_command_time = max(self.selection_command_time, dt)

                    # 自分の選出に追加
                    self.selected[0] = [deepcopy(self.party[0][i]) for i in cmd]

                    # 前の試合のログが開かれたままなら閉じる
                    if logfile is not None and not logfile.closed:
                        logfile.close()

                    # 試合のログを生成
                    filename = 'log/battle/'+datetime.now(timezone(timedelta(hours=+9), 'JST')).strftime('%Y%m%d_%H%M%S')+'.log'
                    print(f'ログ出力 {filename}')
                    logfile = open(filename, 'w', encoding='utf-8')
                    logfile.write(self.dump_party(player=0) + '\n')
                    logfile.write(self.dump_party(player=1) + '\n')

                    self.selection_finished = True
                    self.turn = 0

                case 'battle':
                    t0 = time.time()
                    self.selection_finished = False

                    if not self.read_battle_situlation():
                        warnings.warn('画面認識に失敗しました。再取得します')
                        self.press_button('B', n=4)
                    else:
                        # バッファ内の情報を反映させる
                        self.read_buffer()

                        # 前ターンの終状態を記録
                        if logfile is not None:
                            logfile.write(self.dump() + '\n')

                        # 前ターンの結果を反映
                        for p in self.pokemon:
                            if p.last_pp_move:
                                p.acted_turn += 1

                                if 'こだわり' in p.item and not p.fixed_move:
                                    p.fixed_move = p.last_pp_move

                            if p.ailment == 'SLP' and p.sleep_count > 1:
                                p.sleep_count -= 1

                        # 相手の場のポケモンの観測値を表示
                        self.pokemon[1].show()

                        # コマンドを取得
                        dt = time.time() - t0
                        cmd = self.battle_command(player=0)
                        t0 = time.time()

                        self.turn += 1

                        # コマンドを入力
                        if self.input_battle_command(cmd):
                            # 操作時間を記録
                            dt += time.time() - t0
                            print(f'操作時間 {dt:.1f}s')
                            self.battle_command_time = max(self.battle_command_time, dt)

                            # コマンドを記録
                            self.command[0] = cmd

                            # このターンの行動を反映
                            if cmd in range(10, 20):
                                # テラスタル
                                self.pokemon[0].use_terastal()
                            elif cmd in range(20, 30):
                                # 交代
                                self.change_pokemon(player=0, command=cmd, landing=False)

                            # 連続で認識しないように待つ
                            time.sleep(1)
                        else:
                            warnings.warn(f'コマンド入力を完了できませんでした')
                            self.press_button('B', n=4)
                            continue
                        
                        # 画面の読み取り履歴をクリア
                        self.screen_record.clear()

                case 'change':
                    t0 = time.time()

                    print('場と控えのポケモンのHPを更新')
                    for i in range(len(self.selected[0])):
                        hp = self.read_party_hp(i, capture=(i==0))
                        if hp == 0:
                            hp = self.read_party_hp(i, capture=True) # 0なら再チェック
                        
                        p = Pokemon.find(self.selected[0], display_name=self.read_party_display_name(i))
                        p.hp = hp
                        print(f'\t{p.name} HP {p.hp}/{p.status[0]}')
                        break

                    # バッファ内の情報を反映させる
                    self.read_buffer()

                    # コマンドを取得
                    dt = time.time() - t0
                    cmd = self.change_command(player=0)
                    t0 = time.time()

                    # コマンドを入力
                    self.input_change_command(cmd)

                    # 操作時間を記録
                    dt += time.time() - t0
                    print(f'操作時間 {dt:.1f}')
                    self.change_command_time = max(self.change_command_time, dt)

                    # 交代
                    self.change_pokemon(player=0, command=cmd, landing=False)

                    # 画面の読み取り履歴をクリア
                    self.screen_record.clear()

                    # 連続で認識しないように待つ
                    time.sleep(2)
                
                case _:
                    # 試合中でなければ中断
                    if logfile is None or logfile.closed:
                        continue
                    
                    # 画面下部のテキストを取得
                    if all(self.pokemon) and self.read_bottom_text(capture=False):
                        # 特性発動時のテキストも確認
                        for player in range(2):
                            self.read_ability_text(player, capture=False)
                    
                    # 勝敗を観測したらログを閉じる
                    if not self.vs_NPC:
                        if (result := self.read_win_lose(capture=False)):
                            logfile.write(f'{result}\n')
                            logfile.close()
                    else:
                        self.press_button('A')
                    
                    # 画面の読み取り履歴をクリア
                    self.screen_record.clear()


# デバッグ用
if __name__ == "__main__":
    bot = Pokebot()

    bot.capture('log/capture.png')

    #bot.set_image('log/sample_selection.png')
    #bot.set_image('log/sample_critical.png')
    #bot.set_image('log/enemy_ability.png')

    #bot.read_enemy_party(capture=False)
    #bot.read_bottom_text(capture=False), print(bot.process_buffer)
    #bot.read_ability_text(player=0, capture=False), print(bot.process_buffer)
    #print(bot.selection_cursor_position())
    #bot.trim()

    #img1 = cv2.cvtColor(cv2.imread('log/hp133.png'), cv2.COLOR_BGR2GRAY)
    #img2 = cv2.bitwise_not(img2)
    #print(template_match_score(img1,img2))
    