import NextAuth from "next-auth";
import GithubProvider from "next-auth/providers/github";

const handler = NextAuth({
  providers: [
    GithubProvider({
      clientId: process.env.GITHUB_ID!,
      clientSecret: process.env.GITHUB_SECRET!,
      authorization: { params: { scope: 'repo read:user user:email' } },
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account) {
        token.accessToken = account.access_token;
        token.githubId = profile?.id?.toString() || (profile as any)?.sub;
        token.name = (profile as any)?.login;
        token.avatarUrl = (profile as any)?.avatar_url;
      }
      return token;
    },
    async session({ session, token }: any) {
      session.accessToken = token.accessToken;
      session.githubId = token.githubId;
      session.name = token.name;
      session.avatarUrl = token.avatarUrl;
      return session;
    },
  },
});

export { handler as GET, handler as POST };
