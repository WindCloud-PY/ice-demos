// **********************************************************************
//
// Copyright (c) 2003-2018 ZeroC, Inc. All rights reserved.
//
// **********************************************************************

#include <Ice/Ice.h>
#include <Glacier2/Glacier2.h>
#include <CallbackI.h>

using namespace std;
using namespace Demo;

class CallbackClient : public Glacier2::Application
{
public:

    CallbackClient();

    virtual int runWithSession(int, char*[]) override;
    virtual shared_ptr<Glacier2::SessionPrx> createSession() override;
};

int
main(int argc, char* argv[])
{
#ifdef ICE_STATIC_LIBS
    Ice::registerIceSSL();
#endif
    CallbackClient app;
    return app.main(argc, argv, "config.client");
}

void
menu()
{
    cout <<
        "usage:\n"
        "t: invoke callback as twoway\n"
        "o: invoke callback as oneway\n"
        "O: invoke callback as batch oneway\n"
        "f: flush all batch requests\n"
        "v: set/reset override context field\n"
        "F: set/reset fake category\n"
        "s: shutdown server\n"
        "r: restart the session\n"
        "x: exit\n"
        "?: help\n";
}

CallbackClient::CallbackClient() :
    //
    // Since this is an interactive demo we don't want any signal
    // handling.
    //
    Glacier2::Application(Ice::SignalPolicy::NoSignalHandling)
{
}

shared_ptr<Glacier2::SessionPrx>
CallbackClient::createSession()
{
    shared_ptr<Glacier2::SessionPrx> sess;
    while(!sess)
    {
        cout << "This demo accepts any user-id / password combination.\n";

        string id;
        cout << "user id: " << flush;
        getline(cin, id);

        string pw;
        cout << "password: " << flush;
        getline(cin, pw);

        try
        {
            sess = router()->createSession(id, pw);
            break;
        }
        catch(const Glacier2::PermissionDeniedException& ex)
        {
            cout << "permission denied:\n" << ex.reason << endl;
        }
        catch(const Glacier2::CannotCreateSessionException ex)
        {
            cout << "cannot create session:\n" << ex.reason << endl;
        }
    }
    return sess;
}

int
CallbackClient::runWithSession(int argc, char*[])
{
    if(argc > 1)
    {
        cerr << appName() << ": too many arguments" << endl;
        return EXIT_FAILURE;
    }

    auto callbackReceiverIdent = createCallbackIdentity("callbackReceiver");

    Ice::Identity callbackReceiverFakeIdent;
    callbackReceiverFakeIdent.name = "callbackReceiver";
    callbackReceiverFakeIdent.category = "fake";

    auto base = communicator()->propertyToProxy("Callback.Proxy");
    auto twoway = Ice::checkedCast<CallbackPrx>(base);
    auto oneway = twoway->ice_oneway();
    auto batchOneway = twoway->ice_batchOneway();

    objectAdapter()->add(make_shared<CallbackReceiverI>(), callbackReceiverIdent);

    // Should never be called for the fake identity.
    objectAdapter()->add(make_shared<CallbackReceiverI>(), callbackReceiverFakeIdent);

    auto twowayR = Ice::uncheckedCast<CallbackReceiverPrx>(objectAdapter()->createProxy(callbackReceiverIdent));
    auto onewayR = twowayR->ice_oneway();

    string override;
    bool fake = false;

    menu();

    char c = 'x';
    do
    {
        cout << "==> ";
        cin >> c;
        if(c == 't')
        {
            Ice::Context context;
            context["_fwd"] = "t";
            if(!override.empty())
            {
                context["_ovrd"] = override;
            }
            twoway->initiateCallback(twowayR, context);
        }
        else if(c == 'o')
        {
            Ice::Context context;
            context["_fwd"] = "o";
            if(!override.empty())
            {
                context["_ovrd"] = override;
            }
            oneway->initiateCallback(onewayR, context);
        }
        else if(c == 'O')
        {
            Ice::Context context;
            context["_fwd"] = "O";
            if(!override.empty())
            {
                context["_ovrd"] = override;
            }
            batchOneway->initiateCallback(onewayR, context);
        }
        else if(c == 'f')
        {
            batchOneway->ice_flushBatchRequests();
        }
        else if(c == 'v')
        {
            if(override.empty())
            {
                override = "some_value";
                cout << "override context field is now `" << override << "'" << endl;
            }
            else
            {
                override.clear();
                cout << "override context field is empty" << endl;
            }
        }
        else if(c == 'F')
        {
            fake = !fake;

            if(fake)
            {
                twowayR = Ice::uncheckedCast<CallbackReceiverPrx>(twowayR->ice_identity(callbackReceiverFakeIdent));
                onewayR = Ice::uncheckedCast<CallbackReceiverPrx>(onewayR->ice_identity(callbackReceiverFakeIdent));
            }
            else
            {
                twowayR = Ice::uncheckedCast<CallbackReceiverPrx>(twowayR->ice_identity(callbackReceiverIdent));
                onewayR = Ice::uncheckedCast<CallbackReceiverPrx>(onewayR->ice_identity(callbackReceiverIdent));
            }

            cout << "callback receiver identity: " << Ice::identityToString(twowayR->ice_getIdentity())
                 << endl;
        }
        else if(c == 's')
        {
            twoway->shutdown();
        }
        else if(c == 'r')
        {
            cin.ignore(); // Ignore the new line
            restart();
        }
        else if(c == 'x')
        {
            // Nothing to do
        }
        else if(c == '?')
        {
            menu();
        }
        else
        {
            cout << "unknown command `" << c << "'" << endl;
            menu();
        }
    }
    while(cin.good() && c != 'x');

    return EXIT_SUCCESS;
}
