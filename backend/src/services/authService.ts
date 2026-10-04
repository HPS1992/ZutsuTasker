// import prisma from '../config/prismaClient'; // Simulado

export const authService = {
  async registerUser(email: string, name: string, firebase_uid: string) {
    // 1. Verificar si el usuario ya existe en base de datos PostgreSQL
    // 2. Si no, crearlo: prisma.user.create(...)
    // Retornamos un mock por ahora
    return { id: 'u123', email, name };
  },

  async loginUser(firebase_uid: string) {
    // 1. Buscar usuario por el UID provisto por el token de Firebase
    // 2. Retornar perfil y grupos asociados
    return { id: 'u123', name: 'Álex', token: 'fake_jwt_token' };
  }
};
