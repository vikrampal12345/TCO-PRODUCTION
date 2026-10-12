import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';

import type {
  User,
  AuthState,
  LoginCredentials,
  SignupCredentials,
  UserRole,
} from '../types/auth';

import { supabase } from '../lib/supabase';
import { setAccessToken } from '../services/http';

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  signup: (credentials: SignupCredentials) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(
  undefined
);

function mapSupabaseUser(
  authUser: {
    id: string;
    email?: string;
    user_metadata?: Record<string, unknown>;
  }
): User {
  const metadata = authUser.user_metadata ?? {};

  const roleValue = metadata.role;

  const role: UserRole =
    roleValue === 'Educator' || roleValue === 'Administrator'
      ? roleValue
      : 'Teacher';

  const email = authUser.email ?? '';

  return {
    id: authUser.id,
    name:
      typeof metadata.full_name === 'string' &&
      metadata.full_name.trim()
        ? metadata.full_name
        : email.split('@')[0] || 'Teacher',
    email,
    role,
    school:
      typeof metadata.school === 'string'
        ? metadata.school
        : 'Academic Institution',
    avatarUrl:
      typeof metadata.avatar_url === 'string'
        ? metadata.avatar_url
        : undefined,
  };
}

export const AuthProvider: React.FC<{
  children: React.ReactNode;
}> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const applySession = useCallback(
    (session: {
      access_token: string;
      user: {
        id: string;
        email?: string;
        user_metadata?: Record<string, unknown>;
      };
    } | null) => {
      setAccessToken(session?.access_token ?? null);

      setUser(
        session?.user
          ? mapSupabaseUser(session.user)
          : null
      );
    },
    []
  );

  useEffect(() => {
    let mounted = true;

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (!mounted) return;

        applySession(session);
        setIsLoading(false);
      }
    );

    supabase.auth
      .getSession()
      .then(({ data, error }) => {
        if (!mounted) return;

        if (error) {
          console.error(
            'Unable to restore Supabase session:',
            error.message
          );

          applySession(null);
        } else {
          applySession(data.session);
        }

        setIsLoading(false);
      })
      .catch((error: unknown) => {
        if (!mounted) return;

        console.error(
          'Session initialization failed:',
          error
        );

        applySession(null);
        setIsLoading(false);
      });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [applySession]);

  const login = async (
    credentials: LoginCredentials
  ): Promise<void> => {
    if (!credentials.password) {
      throw new Error('Please enter your password.');
    }

    const { data, error } =
      await supabase.auth.signInWithPassword({
        email: credentials.email.trim(),
        password: credentials.password,
      });

    if (error) {
      throw error;
    }

    if (!data.session) {
      throw new Error(
        'Login did not create an active session. Please try again.'
      );
    }

    applySession(data.session);
  };

  const signup = async (
    credentials: SignupCredentials
  ): Promise<void> => {
    if (!credentials.password) {
      throw new Error('Please enter a password.');
    }

    const { data, error } = await supabase.auth.signUp({
      email: credentials.email.trim().toLowerCase(),
      password: credentials.password,
      options: {
        data: {
          full_name: credentials.name.trim(),
          role: credentials.role,
          school: credentials.school ?? '',
        },
      },
    });

    if (error) {
      throw error;
    }

    if (data.session) {
      applySession(data.session);
    } else {
      applySession(null);
    }
  };

  const loginWithGoogle = async (): Promise<void> => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/workspace`,
      },
    });

    if (error) {
      throw error;
    }

    // Supabase redirects the browser to Google.
    // Do not navigate manually after this call.
  };

  const logout = async (): Promise<void> => {
    const { error } = await supabase.auth.signOut();

    if (error) {
      throw error;
    }

    applySession(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        signup,
        loginWithGoogle,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      'useAuth must be used within an AuthProvider'
    );
  }

  return context;
};