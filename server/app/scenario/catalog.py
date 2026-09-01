"""Server-owned child-safe scenario catalogue."""

from server.app.scenario.domain import SceneDefinition, SceneGoal


SCENES: tuple[SceneDefinition, ...] = (
    SceneDefinition(
        id="restaurant",
        title="At the Restaurant",
        title_zh="餐厅点餐",
        subtitle="和友好的服务员练习点食物、要饮料和礼貌道谢",
        icon="🍽️",
        difficulty="入门",
        partner_role="a friendly waiter",
        opening_line="Hello! Welcome to our restaurant. What would you like today?",
        persona="You are a warm waiter in a simple, fictional family restaurant.",
        goals=(
            SceneGoal("order_food", "点一份食物", "Can I have a sandwich, please?", "试着礼貌地点一份食物。", "The learner understandably asks for a food item."),
            SceneGoal("ask_for_drink", "要一杯饮料", "Can I have some water, please?", "试着说出想喝什么。", "The learner understandably asks for water or another drink."),
            SceneGoal("say_thank_you", "礼貌道谢", "Thank you!", "结束时别忘了说谢谢。", "The learner thanks the partner politely."),
        ),
    ),
    SceneDefinition(
        id="school",
        title="A Day at School",
        title_zh="学校日常",
        subtitle="和同学练习问好、求助和借学习用品",
        icon="🏫",
        difficulty="入门",
        partner_role="a friendly classmate",
        opening_line="Hi! It is nice to see you at school. How are you today?",
        persona="You are a kind classmate in a fictional primary-school classroom.",
        goals=(
            SceneGoal("say_hello", "主动问好", "Hi! How are you?", "先友好地打个招呼。", "The learner greets the partner and asks how they are."),
            SceneGoal("ask_for_help", "请求帮助", "Can you help me, please?", "遇到困难时礼貌求助。", "The learner asks for simple help understandably."),
            SceneGoal("borrow_an_item", "借学习用品", "Can I borrow a pencil, please?", "试着礼貌地借一件学习用品。", "The learner politely asks to borrow a school item."),
        ),
    ),
    SceneDefinition(
        id="shopping",
        title="At the Shop",
        title_zh="商店买东西",
        subtitle="在儿童书店或玩具店练习问价格和挑选商品",
        icon="🛍️",
        difficulty="初级",
        partner_role="a helpful shop assistant",
        opening_line="Hello! Welcome to the toy and book shop. What are you looking for?",
        persona="You are a helpful assistant in a fictional child-friendly toy and book shop.",
        goals=(
            SceneGoal("ask_price", "询问价格", "How much is this?", "选中东西后问问价格。", "The learner asks the price of an item."),
            SceneGoal("choose_item", "选择商品", "I'd like the blue one, please.", "说出自己想要哪一个。", "The learner clearly chooses an item or colour."),
            SceneGoal("say_thank_you", "礼貌道谢", "Thank you!", "买好后礼貌地说谢谢。", "The learner thanks the partner politely."),
        ),
    ),
    SceneDefinition(
        id="travel",
        title="Asking for Directions",
        title_zh="旅行问路",
        subtitle="在信息台练习问路、确认方向和礼貌道谢",
        icon="🗺️",
        difficulty="初级",
        partner_role="a friendly information-desk helper",
        opening_line="Hello! I can help you find a place. Where would you like to go?",
        persona="You are a friendly helper at a fictional visitor information desk. Never ask for personal travel documents or contact details.",
        goals=(
            SceneGoal("ask_directions", "询问路线", "Excuse me, where is the museum?", "先说打扰一下，再问地点。", "The learner asks how to find a place."),
            SceneGoal("understand_direction", "确认方向", "Turn left here?", "把听到的方向简单确认一下。", "The learner checks or confirms a direction."),
            SceneGoal("say_thank_you", "感谢帮助", "Thank you for your help!", "得到帮助后说谢谢。", "The learner thanks the helper."),
        ),
    ),
)

_BY_ID = {scene.id: scene for scene in SCENES}


def get_scene(scene_id: str) -> SceneDefinition | None:
    return _BY_ID.get(scene_id)
