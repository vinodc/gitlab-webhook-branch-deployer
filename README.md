## gitlab-webhook-branch-deployer

Clones and maintains directories with the latest contents of a branch.

Tested and verified to work with Python 2.7.

### Usage

```$ ./gitlab-webhook.py --port 8000 git@github.com:vinodc/gitlab-webhook-branch-deployer.git /home/vinod/gwbd```

This will run the process and listen on port 8000 for POST requests from Gitlab that correspond to the repository ```vinodc/gitlab-webhook-branch-deployer```. When it receives a request, it will clone the branches that were
indicated as having been updated to the directory ```/home/vinod/gwbd```.

It will ignore any branch with a '/' in it's name. This is intentional, to allow for feature branches or similar that will not be cloned.

For help: ```$ ./gitlab-webhook.py -h```

### Deployment

I recommend using http://supervisord.org/ or similar to run the script. For the sake of completion, here are the contents of my supervisord conf.d file:

/etc/supervisor/conf.d/gitlab-webhook.conf
```
command=/usr/bin/env python /opt/githooks/deployer/gitlab-webhook.py --port 8001 git@github.com:vinodc/gitlab-webhook-branch-deployer.git /opt/githooks/gwbd
directory=/opt/githooks/deployer
user=deployer
numprocs=1
autostart=true
process_name=%(program_name)s-%(process_num)02d
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/%(program_name)s-%(process_num)s-stdout.log
```

### Acknowledgements

Inspired by https://github.com/shawn-sterling/gitlab-webhook-receiver.

### License

GPLv2
