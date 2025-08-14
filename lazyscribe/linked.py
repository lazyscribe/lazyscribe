"""Linked list utilities.

The code for this module is lifted from
`here <https://www.educative.io/edpresso/how-to-merge-two-sorted-linked-lists-in-python>`_.
"""

from __future__ import annotations

from typing import Any

from attrs import define


@define
class Node:
    """Node for the linked list.

    Parameters
    ----------
    data : Any, optional (default None)
        The current data.
    next : Node | None, optional (default None)
        The next data in the chain.
    """

    data: Any = None
    next: Node | None = None

    def to_list(self) -> list[Any]:
        """Convert the nodes to a de-duped list.

        Returns
        -------
        list[Any]
            A standard list of data.
        """
        out: list[Any] = []
        while self.next:
            out.append(self.data)
            self = self.next
        out.append(self.data)

        return out


@define
class LinkedList:
    """The linked list.

    Parameters
    ----------
    head : Node, optional (default None)
        The start of the list.
    """

    head: Node | None = None

    def append(self, data: Any) -> None:
        """Append a new node to the end of the list.

        Parameters
        ----------
        data : Any
            The new data.
        """
        new = Node(data=data)
        if self.head:
            # Scroll to the end of the list
            current = self.head
            while current.next:
                current = current.next
            current.next = new
        else:
            self.head = new

    @staticmethod
    def from_list(data: list[Any]) -> LinkedList:
        """Convert a standard list to a linked list."""
        # Sort the list
        sorted_list = sorted(data)
        out = LinkedList()
        for val in sorted_list:
            out.append(val)

        return out


def merge(list1: Node, list2: Node) -> Node:
    """Merge two linked lists.

    Parameters
    ----------
    list1 : Node
        The head of the first list.
    list2 : Node
        The head of the second list.

    Returns
    -------
    Node
        The head of the final, merged list.
    """
    # Create the head of the new list as a dummy node
    head = Node()
    current = head
    # Loop while the data exists
    while list1 and list2:
        # Add the earliest available node from either l1 or l2
        if list1.data < list2.data:
            current.next = list1
            # Scroll the list
            list1: Node | None = list1.next  # type: ignore[no-redef]
        else:
            current.next = list2
            # Scroll the list
            list2: Node | None = list2.next  # type: ignore[no-redef]
        current = current.next
    # Add non-empty list
    current.next = list1 or list2
    return head.next  # type: ignore[return-value]
