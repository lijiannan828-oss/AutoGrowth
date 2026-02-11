/**
 * 贴纸配置 - 包含所有可用的贴纸
 */

export interface StickerItem {
  id: string;
  name: string;
  path: string;
  type: 'image' | 'gif';
}

export interface StickerCategory {
  id: string;
  name: string;
  icon: string;
  stickers: StickerItem[];
}

/**
 * 所有可用的贴纸分类
 */
export const STICKER_CATEGORIES: StickerCategory[] = [
  {
    id: 'cute_animals',
    name: '🐱 可爱动物',
    icon: '🐱',
    stickers: [
      { id: 'cat_wave', name: '猫咪挥手', path: '/stickers/cute_animals/cat_wave.gif', type: 'gif' },
      { id: 'cat_typing', name: '猫咪打字', path: '/stickers/cute_animals/cat_typing.gif', type: 'gif' },
      { id: 'cat_sleep', name: '猫咪睡觉', path: '/stickers/cute_animals/cat_sleep.gif', type: 'gif' },
      { id: 'cat_dance', name: '猫咪跳舞', path: '/stickers/cute_animals/cat_dance.gif', type: 'gif' },
      { id: 'cat_love', name: '猫咪爱心', path: '/stickers/cute_animals/cat_love.gif', type: 'gif' },
      { id: 'dog_happy', name: '狗狗开心', path: '/stickers/cute_animals/dog_happy.gif', type: 'gif' },
      { id: 'dog_run', name: '狗狗跑步', path: '/stickers/cute_animals/dog_run.gif', type: 'gif' },
      { id: 'dog_cute', name: '狗狗卖萌', path: '/stickers/cute_animals/dog_cute.gif', type: 'gif' },
      { id: 'bunny_hop', name: '兔子跳跃', path: '/stickers/cute_animals/bunny_hop.gif', type: 'gif' },
      { id: 'bear_wave', name: '熊熊挥手', path: '/stickers/cute_animals/bear_wave.gif', type: 'gif' },
      { id: 'penguin_walk', name: '企鹅走路', path: '/stickers/cute_animals/penguin_walk.gif', type: 'gif' },
      { id: 'hamster_eat', name: '仓鼠吃东西', path: '/stickers/cute_animals/hamster_eat.gif', type: 'gif' },
    ],
  },
  {
    id: 'memes',
    name: '😂 表情包',
    icon: '😂',
    stickers: [
      { id: 'thinking', name: '思考', path: '/stickers/memes/thinking.gif', type: 'gif' },
      { id: 'shocked', name: '震惊', path: '/stickers/memes/shocked.gif', type: 'gif' },
      { id: 'deal_with_it', name: '墨镜', path: '/stickers/memes/deal_with_it.gif', type: 'gif' },
      { id: 'popcorn', name: '吃瓜', path: '/stickers/memes/popcorn.gif', type: 'gif' },
      { id: 'typing', name: '打字中', path: '/stickers/memes/typing.gif', type: 'gif' },
    ],
  },
  {
    id: 'effects',
    name: '✨ 特效动画',
    icon: '✨',
    stickers: [
      { id: 'sparkle', name: '闪光', path: '/stickers/effects/sparkle.gif', type: 'gif' },
      { id: 'shine', name: '发光', path: '/stickers/effects/shine.gif', type: 'gif' },
      { id: 'star', name: '星星', path: '/stickers/effects/star.gif', type: 'gif' },
      { id: 'rainbow', name: '彩虹', path: '/stickers/effects/rainbow.gif', type: 'gif' },
      { id: 'confetti', name: '彩带', path: '/stickers/effects/confetti.gif', type: 'gif' },
      { id: 'fireworks', name: '烟花', path: '/stickers/effects/fireworks.gif', type: 'gif' },
      { id: 'heart_beat', name: '心跳', path: '/stickers/effects/heart_beat.gif', type: 'gif' },
      { id: 'hearts', name: '爱心', path: '/stickers/effects/hearts.gif', type: 'gif' },
      { id: 'love', name: '爱意', path: '/stickers/effects/love.gif', type: 'gif' },
      { id: 'explosion', name: '爆炸', path: '/stickers/effects/explosion.gif', type: 'gif' },
    ],
  },
  {
    id: 'reactions',
    name: '👍 反应动图',
    icon: '👍',
    stickers: [
      { id: 'yes', name: 'YES', path: '/stickers/reactions/yes.gif', type: 'gif' },
      { id: 'ok', name: 'OK', path: '/stickers/reactions/ok.gif', type: 'gif' },
      { id: 'clap', name: '鼓掌', path: '/stickers/reactions/clap.gif', type: 'gif' },
      { id: 'thumbs_up', name: '点赞', path: '/stickers/reactions/thumbs_up.gif', type: 'gif' },
      { id: 'wave', name: '挥手', path: '/stickers/reactions/wave.gif', type: 'gif' },
    ],
  },
  {
    id: 'emotions',
    name: '😊 情绪表情',
    icon: '😊',
    stickers: [
      { id: 'happy', name: '开心', path: '/stickers/emotions/happy.gif', type: 'gif' },
      { id: 'sad', name: '伤心', path: '/stickers/emotions/sad.gif', type: 'gif' },
      { id: 'cry', name: '哭泣', path: '/stickers/emotions/cry.gif', type: 'gif' },
      { id: 'laugh', name: '大笑', path: '/stickers/emotions/laugh.gif', type: 'gif' },
      { id: 'sleep', name: '睡觉', path: '/stickers/emotions/sleep.gif', type: 'gif' },
      { id: 'tired', name: '疲惫', path: '/stickers/emotions/tired.gif', type: 'gif' },
      { id: 'nervous', name: '紧张', path: '/stickers/emotions/nervous.gif', type: 'gif' },
      { id: 'awkward', name: '尴尬', path: '/stickers/emotions/awkward.gif', type: 'gif' },
    ],
  },
  {
    id: 'cartoon',
    name: '🎭 卡通角色',
    icon: '🎭',
    stickers: [
      { id: 'chibi_happy', name: 'Q版开心', path: '/stickers/cartoon/chibi_happy.gif', type: 'gif' },
      { id: 'chibi_cry', name: 'Q版哭泣', path: '/stickers/cartoon/chibi_cry.gif', type: 'gif' },
      { id: 'chibi_love', name: 'Q版爱心', path: '/stickers/cartoon/chibi_love.gif', type: 'gif' },
      { id: 'chibi_wave', name: 'Q版挥手', path: '/stickers/cartoon/chibi_wave.gif', type: 'gif' },
      { id: 'sticker_ok', name: 'OK贴纸', path: '/stickers/cartoon/sticker_ok.gif', type: 'gif' },
      { id: 'sticker_yes', name: 'YES贴纸', path: '/stickers/cartoon/sticker_yes.gif', type: 'gif' },
    ],
  },
  {
    id: 'celebration',
    name: '🎉 庆祝动图',
    icon: '🎉',
    stickers: [
      { id: 'victory', name: '胜利', path: '/stickers/celebration/victory.gif', type: 'gif' },
      { id: 'congrats', name: '恭喜', path: '/stickers/celebration/congrats.gif', type: 'gif' },
    ],
  },
  {
    id: 'loading',
    name: '⏳ 加载动画',
    icon: '⏳',
    stickers: [
      { id: 'loading_circle', name: '圆圈加载', path: '/stickers/loading/loading_circle.gif', type: 'gif' },
      { id: 'loading_dots', name: '点点加载', path: '/stickers/loading/loading_dots.gif', type: 'gif' },
      { id: 'loading_spinner', name: '旋转加载', path: '/stickers/loading/loading_spinner.gif', type: 'gif' },
      { id: 'loading_cat', name: '猫咪加载', path: '/stickers/loading/loading_cat.gif', type: 'gif' },
      { id: 'loading_rainbow', name: '彩虹加载', path: '/stickers/loading/loading_rainbow.gif', type: 'gif' },
      { id: 'loading_heart', name: '爱心加载', path: '/stickers/loading/loading_heart.gif', type: 'gif' },
    ],
  },
  {
    id: 'badges',
    name: '🏆 徽章标签',
    icon: '🏆',
    stickers: [
      { id: 'hot', name: 'HOT', path: '/stickers/badges/hot.png', type: 'image' },
      { id: 'new', name: 'NEW', path: '/stickers/badges/new.png', type: 'image' },
      { id: 'sale', name: 'SALE', path: '/stickers/badges/sale.png', type: 'image' },
      { id: 'top', name: 'TOP', path: '/stickers/badges/top.png', type: 'image' },
      { id: 'vip', name: 'VIP', path: '/stickers/badges/vip.png', type: 'image' },
    ],
  },
  {
    id: 'emoji',
    name: '😀 Emoji',
    icon: '😀',
    stickers: [
      { id: 'cool', name: '酷', path: '/stickers/emoji/cool.png', type: 'image' },
      { id: 'cry', name: '哭', path: '/stickers/emoji/cry.png', type: 'image' },
      { id: 'fire', name: '火', path: '/stickers/emoji/fire.png', type: 'image' },
      { id: 'heart', name: '爱心', path: '/stickers/emoji/heart.png', type: 'image' },
      { id: 'laugh', name: '笑', path: '/stickers/emoji/laugh.png', type: 'image' },
      { id: 'love', name: '爱', path: '/stickers/emoji/love.png', type: 'image' },
      { id: 'party', name: '派对', path: '/stickers/emoji/party.png', type: 'image' },
      { id: 'shock', name: '震惊', path: '/stickers/emoji/shock.png', type: 'image' },
    ],
  },
];

/**
 * 获取所有贴纸的路径列表
 */
export const getAllStickerPaths = (): string[] => {
  return STICKER_CATEGORIES.flatMap(category => 
    category.stickers.map(sticker => sticker.path)
  );
};

/**
 * 根据 ID 获取贴纸路径
 */
export const getStickerPathById = (id: string): string | null => {
  for (const category of STICKER_CATEGORIES) {
    const sticker = category.stickers.find(s => s.id === id);
    if (sticker) return sticker.path;
  }
  return null;
};

/**
 * 随机获取一个贴纸路径
 */
export const getRandomStickerPath = (): string => {
  const allPaths = getAllStickerPaths();
  return allPaths[Math.floor(Math.random() * allPaths.length)];
};

