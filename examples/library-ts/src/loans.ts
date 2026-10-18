type LoanStatus = "active" | "returned" | "overdue";

interface Book {
  isbn: string;
  title: string;
  copies: number;
}

interface Member {
  id: string;
  name: string;
  maxLoans: number;
}

interface Loan {
  id: string;
  isbn: string;
  memberId: string;
  dueAt: Date;
  status: LoanStatus;
}

class Catalog {
  constructor(private books: Map<string, Book>) {}

  find(isbn: string): Book {
    const book = this.books.get(isbn);
    if (!book) {
      throw new Error(`Unknown book: ${isbn}`);
    }
    return book;
  }

  takeCopy(isbn: string): Book {
    const book = this.find(isbn);
    if (book.copies === 0) {
      throw new Error(`No copies left of ${book.title}`);
    }
    book.copies -= 1;
    return book;
  }
}

function dueDate(from: Date, days = 21): Date {
  const due = new Date(from);
  due.setDate(due.getDate() + days);
  return due;
}

function checkLimit(member: Member, loans: Loan[]): void {
  const open = loans.filter((l) => l.memberId === member.id && l.status !== "returned");
  if (open.length >= member.maxLoans) {
    throw new Error(`${member.name} already has ${open.length} books`);
  }
}

export function lendBook(
  isbn: string,
  member: Member,
  loans: Loan[],
  catalog: Catalog
): Loan {
  checkLimit(member, loans);
  const book = catalog.takeCopy(isbn);
  const loan: Loan = {
    id: crypto.randomUUID(),
    isbn: book.isbn,
    memberId: member.id,
    dueAt: dueDate(new Date()),
    status: "active",
  };
  loans.push(loan);
  return loan;
}
