import type { User } from '@prisma/client';

declare global {
  namespace Express {
    interface Request {
      /** Set by requireAuth before authenticated route handlers run. */
      user: User;
    }
  }
}

export {};
