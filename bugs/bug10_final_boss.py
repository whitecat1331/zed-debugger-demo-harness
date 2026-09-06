"""Bug 10 (final boss): maximum product subarray.

`max_product_subarray(nums)` should return the largest possible product of a
contiguous (non-empty) subarray of `nums`. Negative numbers and zeros are
allowed.

Examples:
    [2, 3, -2, 4]  ->  6   (subarray [2, 3])
    [-2, 0, -1]    ->  0   (subarray [0])
    [-2, 3, -4]    -> 24   (subarray [-2, 3, -4])
    [0, 2]         ->  2
    [-2]           -> -2
"""


def max_product_subarray(nums):
    if not nums:
        return 0

    current_max = nums[0]
    global_max = nums[0]

    for num in nums[1:]:
        current_max = max(num, current_max * num)
        global_max = max(global_max, current_max)

    return global_max
