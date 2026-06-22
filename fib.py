def fibonacci_sequence(n: int):
    """
    生成前 n 个斐波那契数。
    """
    if n <= 0:
        return []
    if n == 1:
        return [0]
    
    sequence = [0, 1]
    while len(sequence) < n:
        sequence.append(sequence[-1] + sequence[-2])
    return sequence

def fibonacci_gen(n: int):
    """
    斐波那契数列的生成器实现。
    """
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

def test_fibonacci():
    # 测试边界条件
    assert fibonacci_sequence(0) == []
    assert fibonacci_sequence(1) == [0]
    assert fibonacci_sequence(2) == [0, 1]
    
    # 测试普通数列生成
    assert fibonacci_sequence(10) == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
    
    # 测试生成器
    gen_result = list(fibonacci_gen(10))
    assert gen_result == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
    
    print("所有斐波那契测试用例均通过！")

if __name__ == '__main__':
    test_fibonacci()
