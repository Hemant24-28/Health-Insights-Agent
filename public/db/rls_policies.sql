ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS hia_users_select_own ON public.users;
CREATE POLICY hia_users_select_own
ON public.users
FOR SELECT
TO authenticated
USING ((SELECT auth.uid()) = id);

DROP POLICY IF EXISTS hia_users_insert_own ON public.users;
CREATE POLICY hia_users_insert_own
ON public.users
FOR INSERT
TO authenticated
WITH CHECK ((SELECT auth.uid()) = id);

DROP POLICY IF EXISTS hia_chat_sessions_select_own ON public.chat_sessions;
CREATE POLICY hia_chat_sessions_select_own
ON public.chat_sessions
FOR SELECT
TO authenticated
USING ((SELECT auth.uid()) = user_id);

DROP POLICY IF EXISTS hia_chat_sessions_insert_own ON public.chat_sessions;
CREATE POLICY hia_chat_sessions_insert_own
ON public.chat_sessions
FOR INSERT
TO authenticated
WITH CHECK ((SELECT auth.uid()) = user_id);

DROP POLICY IF EXISTS hia_chat_sessions_delete_own ON public.chat_sessions;
CREATE POLICY hia_chat_sessions_delete_own
ON public.chat_sessions
FOR DELETE
TO authenticated
USING ((SELECT auth.uid()) = user_id);

DROP POLICY IF EXISTS hia_chat_messages_select_own ON public.chat_messages;
CREATE POLICY hia_chat_messages_select_own
ON public.chat_messages
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.chat_sessions AS s
        WHERE s.id = chat_messages.session_id
          AND s.user_id = (SELECT auth.uid())
    )
);

DROP POLICY IF EXISTS hia_chat_messages_insert_own ON public.chat_messages;
CREATE POLICY hia_chat_messages_insert_own
ON public.chat_messages
FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.chat_sessions AS s
        WHERE s.id = chat_messages.session_id
          AND s.user_id = (SELECT auth.uid())
    )
);

DROP POLICY IF EXISTS hia_chat_messages_delete_own ON public.chat_messages;
CREATE POLICY hia_chat_messages_delete_own
ON public.chat_messages
FOR DELETE
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.chat_sessions AS s
        WHERE s.id = chat_messages.session_id
          AND s.user_id = (SELECT auth.uid())
    )
);
