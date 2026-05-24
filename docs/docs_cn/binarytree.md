# 完全二叉树与数组下标公式

在理解 `heapq`、最小堆（minheap）之前，先要理解一个基础问题：

> 为什么一棵二叉树可以用一个普通数组表示？

答案是：**完全二叉树** 如果按照“从上到下、从左到右”的顺序放进数组，节点之间会天然形成一套下标公式。

这套公式就是最小堆里 `parent`、`left child`、`right child` 的来源。

---

## 一、先看一棵完全二叉树

假设有这样一棵树：

```text
              A
           /     \
          B       C
        /  \     /  \
       D    E   F    G
      / \
     H   I
```

我们把它按照 **从上到下、从左到右** 的顺序放进数组：

```text
index:  0  1  2  3  4  5  6  7  8
node:   A  B  C  D  E  F  G  H  I
```

对应关系就是：

```text
A 的 index 是 0
B 的 index 是 1
C 的 index 是 2
D 的 index 是 3
E 的 index 是 4
F 的 index 是 5
G 的 index 是 6
H 的 index 是 7
I 的 index 是 8
```

这时，树里的 parent / child 关系，就可以转成数组下标关系。

---

## 二、从 parent 找 child

先观察每个节点的左右子节点：

```text
A(0) 的 left 是 B(1)，right 是 C(2)
B(1) 的 left 是 D(3)，right 是 E(4)
C(2) 的 left 是 F(5)，right 是 G(6)
D(3) 的 left 是 H(7)，right 是 I(8)
```

把下标单独拿出来看：

```text
i = 0 -> left = 1, right = 2
i = 1 -> left = 3, right = 4
i = 2 -> left = 5, right = 6
i = 3 -> left = 7, right = 8
```

你会看到规律：

```python
left = 2 * i + 1
right = 2 * i + 2
```

其中 `i` 就是当前 parent 节点的下标。

验证一下：

```python
i = 0
left = 2 * 0 + 1   # 1
right = 2 * 0 + 2  # 2

i = 1
left = 2 * 1 + 1   # 3
right = 2 * 1 + 2  # 4

i = 2
left = 2 * 2 + 1   # 5
right = 2 * 2 + 2  # 6
```

所以在数组表示的完全二叉树里：

> 当前节点下标是 `i`，它的左子节点是 `2 * i + 1`，右子节点是 `2 * i + 2`。

---

## 三、从 child 找 parent

那如果我们知道一个节点的下标，怎么找到它的 parent？

公式是：

```python
parent = (index - 1) // 2
```

这里的 `index` 是当前节点的下标。

`//` 是整除，意思是只保留整数商，不保留小数部分。

验证一下：

```python
index = 1
parent = (1 - 1) // 2  # 0

index = 2
parent = (2 - 1) // 2  # 0
```

`1` 和 `2` 的 parent 都是 `0`，也就是：

```text
B(1) 和 C(2) 的 parent 都是 A(0)
```

再看下一组：

```python
index = 3
parent = (3 - 1) // 2  # 1

index = 4
parent = (4 - 1) // 2  # 1
```

`3` 和 `4` 的 parent 都是 `1`，也就是：

```text
D(3) 和 E(4) 的 parent 都是 B(1)
```

---

## 四、为什么 parent 公式是 `(index - 1) // 2`？

因为 child 公式可以反推回来。

如果某个节点是 left child：

```python
child = 2 * parent + 1
```

反推：

```python
parent = (child - 1) // 2
```

如果某个节点是 right child：

```python
child = 2 * parent + 2
```

反推：

```python
parent = (child - 2) // 2
```

但是在代码里，我们不想先判断“当前节点是 left child 还是 right child”。所以统一使用：

```python
parent = (index - 1) // 2
```

这个公式对 left child 和 right child 都成立。

为什么 right child 也成立？

因为整除 `//` 会丢掉小数部分：

```python
index = 2
parent = (2 - 1) // 2
parent = 1 // 2
parent = 0
```

`2` 是 `0` 的 right child，公式仍然能得到正确 parent。

---

## 五、为什么完全二叉树适合放进数组？

二叉树每一层的节点数量大概是翻倍增长：

```text
第 0 层：1 个节点
第 1 层：2 个节点
第 2 层：4 个节点
第 3 层：8 个节点
```

如果它是完全二叉树，节点会从左到右连续填满，中间不会留下空洞。

所以它放进数组后，下标也是连续的：

```text
0, 1, 2, 3, 4, 5, 6, 7, ...
```

正因为下标连续，才可以用公式直接计算 parent 和 child，不需要每个节点额外保存指针。

这也是堆结构喜欢用数组实现的原因：简单、紧凑、计算快。

---

## 六、和 minheap 有什么关系？

最小堆本质上就是一棵满足特殊规则的完全二叉树：

> 每个 parent 节点都不大于自己的 child 节点。

在 minheap 里，经常需要做两件事：

1. 新元素插入到数组末尾后，向上和 parent 比较。
2. 堆顶被弹出后，新堆顶向下和 left / right child 比较。

所以 minheap 需要频繁使用这三个公式：

```python
parent = (index - 1) // 2
left = 2 * index + 1
right = 2 * index + 2
```

对应到代码里：

```python
def _sift_up(index):
    parent = (index - 1) // 2


def _sift_down(index):
    left = 2 * index + 1
    right = 2 * index + 2
```

一句话总结：

> 完全二叉树让“树结构”可以放进数组；数组下标公式让 minheap 可以快速找到 parent 和 child。
