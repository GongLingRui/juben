**analysis_type**: 人物关系分析

### characters

1.   **name**: 林晓

  **role**: 主角

  **description**: 刚毕业的职场新人，焦虑迷茫

  **importance**: 8

2.   **name**: 张阿姨

  **role**: 配角

  **description**: 街角奶茶店老板，温柔热心

  **importance**: 8

3.   **name**: 路人甲

  **role**: 配角

  **description**: 奶茶店顾客，背景角色

  **importance**: 5


### relationships

1.   **character1**: 林晓

  **character2**: 张阿姨

  **relationship_type**: friendship

  **description**: 林晓和张阿姨是朋友关系，张阿姨在林晓迷茫时给予安慰和支持。

  **strength**: 8

  **stage**: 发展期

  ### key_events

  1. 林晓进入奶茶店寻求帮助
  2. 张阿姨给予林晓温暖和鼓励

  **relationship_type_cn**: 友情关系

  **sentiment**: positive

2.   **character1**: 林晓

  **character2**: 路人甲

  **relationship_type**: stranger

  **description**: 林晓和路人甲在奶茶店相遇，但两人没有明显的互动。

  **strength**: 2

  **stage**: 初期

  ### key_events

  1. 路人甲进入奶茶店

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral

3.   **character1**: 张阿姨

  **character2**: 路人甲

  **relationship_type**: stranger

  **description**: 张阿姨和路人甲是店家和顾客的关系，没有深入的互动。

  **strength**: 2

  **stage**: 初期

  ### key_events

  1. 路人甲购买珍珠奶茶

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral

4.   **character1**: 林晓

  **character2**: 张阿姨

  **relationship_type**: mentor

  **description**: 张阿姨在林晓面临困难时给予职业建议和生活鼓励，起到导师的作用。

  **strength**: 9

  **stage**: 发展期

  ### key_events

  1. 张阿姨分享自己的经历
  2. 张阿姨鼓励林晓

  **relationship_type_cn**: 师徒/指导关系

  **sentiment**: neutral

5.   **character1**: 路人甲

  **character2**: 张阿姨

  **relationship_type**: stranger

  **description**: 路人甲和张阿姨是顾客和店家的关系，没有特别的互动。

  **strength**: 2

  **stage**: 初期

  ### key_events

  1. 路人甲购买珍珠奶茶

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral

6.   **character1**: 林晓

  **character2**: 路人甲

  **relationship_type**: stranger

  **description**: 林晓和路人甲是奶茶店内的陌生人，没有直接的交流。

  **strength**: 2

  **stage**: 初期

  ### key_events

  1. 林晓和路人甲在同一时间内进入奶茶店

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral

7.   **character1**: 张阿姨

  **character2**: 路人甲

  **relationship_type**: stranger

  **description**: 张阿姨和路人甲在奶茶店相遇，但两人没有深入的互动。

  **strength**: 2

  **stage**: 初期

  ### key_events

  1. 路人甲进入奶茶店购买珍珠奶茶

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral

8.   **character1**: 林晓

  **character2**: 张阿姨

  **relationship_type**: ally

  **description**: 林晓和张阿姨在困境中互相支持，成为彼此的盟友。

  **strength**: 8

  **stage**: 发展期

  ### key_events

  1. 林晓在奶茶店寻求帮助
  2. 张阿姨给予林晓帮助和鼓励

  **relationship_type_cn**: 盟友关系

  **sentiment**: positive

9.   **character1**: 张阿姨

  **character2**: 路人甲

  **relationship_type**: stranger

  **description**: 张阿姨和路人甲是顾客和店家的关系，没有特别的互动。

  **strength**: 2

  **stage**: 初期

  ### key_events

  1. 路人甲购买珍珠奶茶

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral

10.   **character1**: 林晓

  **character2**: 路人甲

  **relationship_type**: stranger

  **description**: 林晓和路人甲在奶茶店相遇，但两人没有直接的交流。

  **strength**: 2

  **stage**: 初期

  ### key_events

  1. 林晓和路人甲在同一时间内进入奶茶店

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral

11.   **character1**: 路人甲

  **character2**: 张阿姨

  **relationship_type**: stranger

  **description**: 路人甲和张阿姨是顾客和店家的关系，没有特别的互动。

  **strength**: 2

  **stage**: 初期

  ### key_events

  1. 路人甲进入奶茶店购买珍珠奶茶

  **relationship_type_cn**: 陌生人关系

  **sentiment**: neutral


## relationship_network

  ### nodes

  1.     **id**: 林晓

    **label**: 林晓

    **role**: 主角

    **importance**: 8

    **description**: 刚毕业的职场新人，焦虑迷茫

  2.     **id**: 张阿姨

    **label**: 张阿姨

    **role**: 配角

    **importance**: 8

    **description**: 街角奶茶店老板，温柔热心

  3.     **id**: 路人甲

    **label**: 路人甲

    **role**: 配角

    **importance**: 5

    **description**: 奶茶店顾客，背景角色


  ### edges

  1.     **source**: 林晓

    **target**: 张阿姨

    **label**: 友情关系

    **strength**: 8

    **type**: friendship

    **sentiment**: positive

  2.     **source**: 林晓

    **target**: 路人甲

    **label**: 陌生人关系

    **strength**: 2

    **type**: stranger

    **sentiment**: neutral

  3.     **source**: 张阿姨

    **target**: 路人甲

    **label**: 陌生人关系

    **strength**: 2

    **type**: stranger

    **sentiment**: neutral

  4.     **source**: 林晓

    **target**: 张阿姨

    **label**: 师徒/指导关系

    **strength**: 9

    **type**: mentor

    **sentiment**: neutral

  5.     **source**: 路人甲

    **target**: 张阿姨

    **label**: 陌生人关系

    **strength**: 2

    **type**: stranger

    **sentiment**: neutral

  6.     **source**: 林晓

    **target**: 路人甲

    **label**: 陌生人关系

    **strength**: 2

    **type**: stranger

    **sentiment**: neutral

  7.     **source**: 张阿姨

    **target**: 路人甲

    **label**: 陌生人关系

    **strength**: 2

    **type**: stranger

    **sentiment**: neutral

  8.     **source**: 林晓

    **target**: 张阿姨

    **label**: 盟友关系

    **strength**: 8

    **type**: ally

    **sentiment**: positive

  9.     **source**: 张阿姨

    **target**: 路人甲

    **label**: 陌生人关系

    **strength**: 2

    **type**: stranger

    **sentiment**: neutral

  10.     **source**: 林晓

    **target**: 路人甲

    **label**: 陌生人关系

    **strength**: 2

    **type**: stranger

    **sentiment**: neutral

  11.     **source**: 路人甲

    **target**: 张阿姨

    **label**: 陌生人关系

    **strength**: 2

    **type**: stranger

    **sentiment**: neutral


  ## statistics

    **total_nodes**: 3

    **total_edges**: 11

    ## node_degrees

      **林晓**: 6

      **张阿姨**: 8

      **路人甲**: 8

    ### key_characters

    1. 张阿姨
    2. 路人甲
    3. 林晓

**summary_report**: ## 人物关系分析报告

### 人物统计
- 总人物数：3
- 总关系对数：11

### 关系类型分布
- 陌生人关系：8对
- 友情关系：1对
- 师徒/指导关系：1对
- 盟友关系：1对

### 关键人物（连接数最多）
- 张阿姨：8个关系
- 路人甲：8个关系
- 林晓：6个关系

### 重要关系
- 林晓 ↔ 张阿姨：师徒/指导关系（强度：9/10）
- 林晓 ↔ 张阿姨：友情关系（强度：8/10）
- 林晓 ↔ 张阿姨：盟友关系（强度：8/10）

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

