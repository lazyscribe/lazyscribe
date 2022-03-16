"""Test linked list utilities."""

from lazyscribe.linked import Node, LinkedList, merge


def test_convert_to_list():
    """Test converting a node to a list."""
    node = Node(1, next=Node(1, Node(2, Node(3, Node(4)))))

    assert node.to_list() == [1, 1, 2, 3, 4]


def test_append_linked_list():
    """Test appending to a linked list."""
    null = LinkedList()
    null.append(3)

    assert null.head == Node(3)

    null.append(4)

    assert null.head == Node(3, next=Node(4))


def test_linked_list_conversion():
    """Test converting a list of integers to a sorted linked list."""
    lst = [1, 2, 1, 3, 4]
    new = LinkedList.from_list(lst)

    assert new == LinkedList(
        head=Node(
            data=1,
            next=Node(
                data=1,
                next=Node(data=2, next=Node(data=3, next=Node(data=4, next=None))),
            ),
        )
    )


def test_merge_no_overlap():
    """Test merging two non-overlapping linked lists"""
    first = LinkedList()
    first.append(1)
    first.append(3)
    first.append(5)
    second = LinkedList()
    second.append(2)
    second.append(4)
    second.append(6)

    out = merge(first.head, second.head)

    assert out == Node(1, Node(2, Node(3, Node(4, Node(5, Node(6))))))


def test_merge_overlap():
    """Test merging with some overlapping nodes."""
    first = LinkedList()
    first.append(1)
    first.append(2)
    first.append(3)
    first.append(5)

    second = LinkedList()
    second.append(1)
    second.append(2)
    second.append(3)
    second.append(4)
    second.append(6)

    out = merge(first.head, second.head)

    assert out == Node(
        1, Node(1, Node(2, Node(2, Node(3, Node(3, Node(4, Node(5, Node(6))))))))
    )
