**analysis_type**: 人物关系分析

### characters

1.   **name**: 林晓

  **role**: 主角

  **description**: 刚毕业的职场新人，焦虑迷茫，性格坚韧。

  **importance**: 8

2.   **name**: 张阿姨

  **role**: 核心配角

  **description**: 街角奶茶店老板，温柔热心，富有同理心。

  **importance**: 8

3.   **name**: 路人甲

  **role**: 配角

  **description**: 街角奶茶店的顾客，普通路人。

  **importance**: 5


### relationships

1.   **character1**: 林晓

  **character2**: 张阿姨

  **relationship_type**: mentor

  **description**: 张阿姨作为奶茶店老板和林晓的聊天中，给予林晓职业和生活上的建议和鼓励。

  **strength**: 8

  **stage**: 发展期

  ### key_events

  1. 张阿姨听林晓讲述求职困难，并分享自己的经历鼓励林晓。
  2. 张阿姨送林晓一杯热奶茶，表达对她的关心和支持。

  **relationship_type_cn**: 师徒/指导关系

  **sentiment**: neutral

2.   **character1**: 林晓

  **character2**: 路人甲

  **relationship_type**: stranger

  **description**: 林晓和路人甲在奶茶店是互不相识的路人。

  **strength**: 1

  **stage**: 初期

  ### key_events

  1. 路人甲进店买奶茶，与林晓和张阿姨无互动。

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral

3.   **character1**: 张阿姨

  **character2**: 路人甲

  **relationship_type**: stranger

  **description**: 张阿姨和路人甲在奶茶店是互不相识的路人。

  **strength**: 1

  **stage**: 初期

  ### key_events

  1. 路人甲进店买奶茶，与张阿姨和林晓无互动。

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral

4.   **character1**: 林晓

  **character2**: 林晓自己

  **relationship_type**: self

  **description**: 林晓对自己的感受和行动有所认知。

  **strength**: 10

  **stage**: 稳定期

  ### key_events

  1. 林晓在奶茶店面对求职挫折，自我反思。
  2. 林晓在留言墙上写下鼓励自己的话语。

  **relationship_type_cn**: 其他关系

  **sentiment**: neutral

5.   **character1**: 张阿姨

  **character2**: 张阿姨自己

  **relationship_type**: self

  **description**: 张阿姨对自己的经历和情感有所认知。

  **strength**: 10

  **stage**: 稳定期

  ### key_events

  1. 张阿姨回忆起自己的过去，与林晓分享自己的故事。

  **relationship_type_cn**: 其他关系

  **sentiment**: neutral

6.   **character1**: 路人甲

  **character2**: 路人甲自己

  **relationship_type**: self

  **description**: 路人甲对自己的需求和行动有所认知。

  **strength**: 10

  **stage**: 稳定期

  ### key_events

  1. 路人甲进入奶茶店购买珍珠奶茶。

  **relationship_type_cn**: 其他关系

  **sentiment**: neutral

7.   **character1**: 林晓

  **character2**: 面试官

  **relationship_type**: antagonistic

  **description**: 林晓和面试官之间存在面试未通过的对立关系。

  **strength**: 4

  **stage**: 结束期

  ### key_events

  1. 林晓多次面试未通过，感到失落。

  **relationship_type_cn**: 对抗/敌对关系

  **sentiment**: neutral

8.   **character1**: 林晓

  **character2**: 张阿姨

  **relationship_type**: ally

  **description**: 林晓和张阿姨在情感上形成了同盟。

  **strength**: 9

  **stage**: 发展期

  ### key_events

  1. 张阿姨送林晓奶茶，并鼓励她。
  2. 林晓感谢张阿姨的帮助。

  **relationship_type_cn**: 盟友关系

  **sentiment**: neutral

9.   **character1**: 张阿姨

  **character2**: 林晓

  **relationship_type**: ally

  **description**: 张阿姨和林晓在情感上形成了同盟。

  **strength**: 9

  **stage**: 发展期

  ### key_events

  1. 张阿姨倾听林晓的烦恼，并给予支持。
  2. 张阿姨送林晓奶茶，表达关心。

  **relationship_type_cn**: 盟友关系

  **sentiment**: neutral

10.   **character1**: 林晓

  **character2**: 路人甲

  **relationship_type**: stranger

  **description**: 林晓和路人甲在奶茶店是互不相识的路人。

  **strength**: 1

  **stage**: 初期

  ### key_events

  1. 路人甲进店买奶茶，与林晓无互动。

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral

11.   **character1**: 路人甲

  **character2**: 林晓

  **relationship_type**: stranger

  **description**: 路人甲和林晓在奶茶店是互不相识的路人。

  **strength**: 1

  **stage**: 初期

  ### key_events

  1. 路人甲进店买奶茶，与林晓无互动。

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral


## relationship_network

  ### nodes

  1.     **id**: 林晓

    **label**: 林晓

    **role**: 主角

    **importance**: 8

    **description**: 刚毕业的职场新人，焦虑迷茫，性格坚韧。

  2.     **id**: 张阿姨

    **label**: 张阿姨

    **role**: 核心配角

    **importance**: 8

    **description**: 街角奶茶店老板，温柔热心，富有同理心。

  3.     **id**: 路人甲

    **label**: 路人甲

    **role**: 配角

    **importance**: 5

    **description**: 街角奶茶店的顾客，普通路人。


  ### edges

  1.     **source**: 林晓

    **target**: 张阿姨

    **label**: 师徒/指导关系

    **strength**: 8

    **type**: mentor

    **sentiment**: neutral

  2.     **source**: 林晓

    **target**: 路人甲

    **label**: 陌生人关系

    **strength**: 1

    **type**: stranger

    **sentiment**: neutral

  3.     **source**: 张阿姨

    **target**: 路人甲

    **label**: 陌生人关系

    **strength**: 1

    **type**: stranger

    **sentiment**: neutral

  4.     **source**: 林晓

    **target**: 林晓自己

    **label**: 其他关系

    **strength**: 10

    **type**: self

    **sentiment**: neutral

  5.     **source**: 张阿姨

    **target**: 张阿姨自己

    **label**: 其他关系

    **strength**: 10

    **type**: self

    **sentiment**: neutral

  6.     **source**: 路人甲

    **target**: 路人甲自己

    **label**: 其他关系

    **strength**: 10

    **type**: self

    **sentiment**: neutral

  7.     **source**: 林晓

    **target**: 面试官

    **label**: 对抗/敌对关系

    **strength**: 4

    **type**: antagonistic

    **sentiment**: neutral

  8.     **source**: 林晓

    **target**: 张阿姨

    **label**: 盟友关系

    **strength**: 9

    **type**: ally

    **sentiment**: neutral

  9.     **source**: 张阿姨

    **target**: 林晓

    **label**: 盟友关系

    **strength**: 9

    **type**: ally

    **sentiment**: neutral

  10.     **source**: 林晓

    **target**: 路人甲

    **label**: 陌生人关系

    **strength**: 1

    **type**: stranger

    **sentiment**: neutral

  11.     **source**: 路人甲

    **target**: 林晓

    **label**: 陌生人关系

    **strength**: 1

    **type**: stranger

    **sentiment**: neutral


  ## statistics

    **total_nodes**: 3

    **total_edges**: 11

    ## node_degrees

      **林晓**: 8

      **张阿姨**: 5

      **路人甲**: 5

      **林晓自己**: 1

      **张阿姨自己**: 1

      **路人甲自己**: 1

      **面试官**: 1

    ### key_characters

    1. 林晓
    2. 张阿姨
    3. 路人甲

**summary_report**: ## 人物关系分析报告

### 人物统计
- 总人物数：3
- 总关系对数：11

### 关系类型分布
- 陌生人关系：4对
- 其他关系：3对
- 盟友关系：2对
- 师徒/指导关系：1对
- 对抗/敌对关系：1对

### 关键人物（连接数最多）
- 林晓：8个关系
- 张阿姨：5个关系
- 路人甲：5个关系

### 重要关系
- 林晓 ↔ 林晓自己：其他关系（强度：10/10）
- 张阿姨 ↔ 张阿姨自己：其他关系（强度：10/10）
- 路人甲 ↔ 路人甲自己：其他关系（强度：10/10）
- 林晓 ↔ 张阿姨：盟友关系（强度：9/10）
- 张阿姨 ↔ 林晓：盟友关系（强度：9/10）

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

