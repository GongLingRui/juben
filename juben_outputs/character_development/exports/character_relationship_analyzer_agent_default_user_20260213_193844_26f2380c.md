**analysis_type**: 人物关系分析

### characters

1.   **name**: 林晓

  **role**: 主角

  **description**: 刚毕业的职场新人，面试失败后情绪低落，后在张阿姨的鼓励下重拾信心。

  **importance**: 8

2.   **name**: 张阿姨

  **role**: 配角

  **description**: 奶茶店老板，用温暖和鼓励帮助林晓，分享个人经历。

  **importance**: 8

3.   **name**: 面试官

  **role**: 配角

  **description**: 林晓面试的面试官，未在故事中直接出现。

  **importance**: 5


### relationships

1.   **character1**: 林晓

  **character2**: 张阿姨

  **relationship_type**: mentor

  **description**: 林晓与张阿姨是师生关系，张阿姨作为奶茶店老板和人生导师，给予林晓职业和情感上的支持。

  **strength**: 8

  **stage**: 发展期

  ### key_events

  1. 林晓面试失败情绪低落
  2. 张阿姨给予鼓励和温暖

  **relationship_type_cn**: 师徒/指导关系

  **sentiment**: positive

2.   **character1**: 林晓

  **character2**: 面试官

  **relationship_type**: antagonistic

  **description**: 林晓与面试官是求职者和面试官的对立关系，面试官的面试过程是林晓面临的挑战。

  **strength**: 4

  **stage**: 初期

  ### key_events

  1. 林晓面试失败

  **relationship_type_cn**: 对抗/敌对关系

  **sentiment**: neutral

3.   **character1**: 张阿姨

  **character2**: 面试官

  **relationship_type**: stranger

  **description**: 张阿姨和面试官在故事中没有交集，是彼此的陌生人。

  **strength**: 1

  **stage**: 初期

  ### key_events

  1. 面试官未在故事中直接出现

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral

4.   **character1**: 林晓

  **character2**: 林晓

  **relationship_type**: self

  **description**: 林晓与自己是自我反思和自我成长的关系。

  **strength**: 10

  **stage**: 发展期

  ### key_events

  1. 林晓面试失败后情绪低落
  2. 林晓重拾信心

  **relationship_type_cn**: 其他关系

  **sentiment**: neutral

5.   **character1**: 张阿姨

  **character2**: 张阿姨

  **relationship_type**: self

  **description**: 张阿姨与自己是个人情感和经历分享的关系。

  **strength**: 10

  **stage**: 稳定期

  ### key_events

  1. 张阿姨分享个人经历

  **relationship_type_cn**: 其他关系

  **sentiment**: neutral

6.   **character1**: 林晓

  **character2**: 张阿姨

  **relationship_type**: ally

  **description**: 林晓和张阿姨是精神上的盟友，张阿姨在林晓困难时提供了帮助。

  **strength**: 8

  **stage**: 发展期

  ### key_events

  1. 张阿姨鼓励林晓，林晓情绪好转

  **relationship_type_cn**: 盟友关系

  **sentiment**: positive

7.   **character1**: 林晓

  **character2**: 面试官

  **relationship_type**: ally

  **description**: 虽然面试官在故事中未出现，但林晓通过面试官的经历可以学习，可以视为一种精神上的盟友关系。

  **strength**: 3

  **stage**: 初期

  ### key_events

  1. 林晓通过面试官的经历进行自我提升

  **relationship_type_cn**: 盟友关系

  **sentiment**: neutral

8.   **character1**: 张阿姨

  **character2**: 林晓

  **relationship_type**: ally

  **description**: 张阿姨和林晓在情感上形成了同盟，共同面对生活中的挑战。

  **strength**: 8

  **stage**: 发展期

  ### key_events

  1. 张阿姨鼓励林晓，林晓重拾信心

  **relationship_type_cn**: 盟友关系

  **sentiment**: neutral

9.   **character1**: 面试官

  **character2**: 张阿姨

  **relationship_type**: stranger

  **description**: 面试官和张阿姨在故事中没有交集，是彼此的陌生人。

  **strength**: 1

  **stage**: 初期

  ### key_events

  1. 面试官未在故事中直接出现

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral

10.   **character1**: 林晓

  **character2**: 面试官

  **relationship_type**: stranger

  **description**: 林晓和面试官在故事中没有直接的互动，是彼此的陌生人。

  **strength**: 1

  **stage**: 初期

  ### key_events

  1. 林晓面试失败

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral

11.   **character1**: 张阿姨

  **character2**: 面试官

  **relationship_type**: stranger

  **description**: 张阿姨和面试官在故事中没有交集，是彼此的陌生人。

  **strength**: 1

  **stage**: 初期

  ### key_events

  1. 面试官未在故事中直接出现

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral


## relationship_network

  ### nodes

  1.     **id**: 林晓

    **label**: 林晓

    **role**: 主角

    **importance**: 8

    **description**: 刚毕业的职场新人，面试失败后情绪低落，后在张阿姨的鼓励下重拾信心。

  2.     **id**: 张阿姨

    **label**: 张阿姨

    **role**: 配角

    **importance**: 8

    **description**: 奶茶店老板，用温暖和鼓励帮助林晓，分享个人经历。

  3.     **id**: 面试官

    **label**: 面试官

    **role**: 配角

    **importance**: 5

    **description**: 林晓面试的面试官，未在故事中直接出现。


  ### edges

  1.     **source**: 林晓

    **target**: 张阿姨

    **label**: 师徒/指导关系

    **strength**: 8

    **type**: mentor

    **sentiment**: positive

  2.     **source**: 林晓

    **target**: 面试官

    **label**: 对抗/敌对关系

    **strength**: 4

    **type**: antagonistic

    **sentiment**: neutral

  3.     **source**: 张阿姨

    **target**: 面试官

    **label**: 陌生人关系

    **strength**: 1

    **type**: stranger

    **sentiment**: neutral

  4.     **source**: 林晓

    **target**: 林晓

    **label**: 其他关系

    **strength**: 10

    **type**: self

    **sentiment**: neutral

  5.     **source**: 张阿姨

    **target**: 张阿姨

    **label**: 其他关系

    **strength**: 10

    **type**: self

    **sentiment**: neutral

  6.     **source**: 林晓

    **target**: 张阿姨

    **label**: 盟友关系

    **strength**: 8

    **type**: ally

    **sentiment**: positive

  7.     **source**: 林晓

    **target**: 面试官

    **label**: 盟友关系

    **strength**: 3

    **type**: ally

    **sentiment**: neutral

  8.     **source**: 张阿姨

    **target**: 林晓

    **label**: 盟友关系

    **strength**: 8

    **type**: ally

    **sentiment**: neutral

  9.     **source**: 面试官

    **target**: 张阿姨

    **label**: 陌生人关系

    **strength**: 1

    **type**: stranger

    **sentiment**: neutral

  10.     **source**: 林晓

    **target**: 面试官

    **label**: 陌生人关系

    **strength**: 1

    **type**: stranger

    **sentiment**: neutral

  11.     **source**: 张阿姨

    **target**: 面试官

    **label**: 陌生人关系

    **strength**: 1

    **type**: stranger

    **sentiment**: neutral


  ## statistics

    **total_nodes**: 3

    **total_edges**: 11

    ## node_degrees

      **林晓**: 8

      **张阿姨**: 8

      **面试官**: 6

    ### key_characters

    1. 林晓
    2. 张阿姨
    3. 面试官

**summary_report**: ## 人物关系分析报告

### 人物统计
- 总人物数：3
- 总关系对数：11

### 关系类型分布
- 陌生人关系：4对
- 盟友关系：3对
- 其他关系：2对
- 师徒/指导关系：1对
- 对抗/敌对关系：1对

### 关键人物（连接数最多）
- 林晓：8个关系
- 张阿姨：8个关系
- 面试官：6个关系

### 重要关系
- 林晓 ↔ 林晓：其他关系（强度：10/10）
- 张阿姨 ↔ 张阿姨：其他关系（强度：10/10）
- 林晓 ↔ 张阿姨：师徒/指导关系（强度：8/10）
- 林晓 ↔ 张阿姨：盟友关系（强度：8/10）
- 张阿姨 ↔ 林晓：盟友关系（强度：8/10）

## metadata

  **agent**: character_relationship_analyzer_agent

  **format_version**: 1.0

  ## relationship_types

    **family**: 家庭关系

    **romantic**: 恋爱关系

    **friendship**: 友情关系

    **work**: 工作/同事关系

    **antagonistic**: 对抗/敌对关系

    **mentor**: 师徒/指导关系

    **rival**: 竞争关系

    **ally**: 盟友关系

    **stranger**: 陌生人关系

    **other**: 其他关系

