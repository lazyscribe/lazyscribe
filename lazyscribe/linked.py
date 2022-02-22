"""Linked list utilities.

The code for this module is lifted from
`here <https://www.educative.io/edpresso/how-to-merge-two-sorted-linked-lists-in-python>`_.
"""

from __future__ import annotations

from typing import Any, List

from attrs import define


@define
class Node:
    """Node for the linked list.

    Parameters
    ----------
    data : any, optional (default None)
        The current data.
    next : any, optional (default None)
        The next data in the chain.
    """

    data: Any = None
    next: Any = None

    def to_list(self) -> List:
        """Convert the nodes to a de-duped list.

        Returns
        -------
        list
            A standard list.
        """
        out = []
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
    head : any, optional (default None)
        The start of the list.
    """

    head: Any = None

    def append(self, data: Any):
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
    def from_list(data: List) -> LinkedList:
        """Convert a standard list to a linked list."""
        # Sort the list
        sorted_list = sorted(data)
        out = LinkedList()
        for val in sorted_list:
            out.append(val)

        return out


def merge(list1: Node, list2: Node) -> Any:
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
    temp = head
    # Loop while some data exists in the latest node
    while list1 or list2:
        # Add the earliest available node from either l1 or l2
        if list1 and (not list2 or list1.data < list2.data):
            temp.next = Node(list1.data)
            # Scroll the list
            list1 = list1.next
        else:
            temp.next = Node(list2.data)
            # Scroll the list
            list2 = list2.next
        temp = temp.next

    return head.next
