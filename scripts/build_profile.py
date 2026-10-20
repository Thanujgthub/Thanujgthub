#!/usr/bin/env python3
"""Refresh the profile's SVG assets from public GitHub data.

Run with GITHUB_TOKEN in Actions, or use --local with an authenticated gh CLI.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import urllib.request
from datetime import datetime, timezone
from build_dashboard import esc, relative_time, compute_streaks, render_svg

ROOT = Path(__file__).resolve().parent.parent
QUERY = '''query($login: String!, $cursor: String) {
  user(login: $login) {
    login name createdAt avatarUrl
    followers { totalCount }
    following { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(privacy: PUBLIC, includeUserRepositories: false) { totalCount }
    contributionsCollection {
      totalCommitContributions totalPullRequestReviewContributions restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, after: $cursor, privacy: PUBLIC, ownerAffiliations: OWNER,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount pageInfo { hasNextPage endCursor }
      nodes {
        name isFork stargazerCount forkCount pushedAt
        primaryLanguage { name color }
        defaultBranchRef {
          target { ... on Commit { history(first: 1) { nodes { message committedDate } } } }
        }
      }
    }
  }
}'''

def graphql(username, cursor, local):
    if local:
        command = ['gh', 'api', 'graphql', '-f', f'query={QUERY}', '-f', f'login={username}']
        if cursor:
            command += ['-f', f'cursor={cursor}']
        payload = json.loads(subprocess.check_output(command, text=True, encoding='utf-8'))
    else:
        token = os.environ.get('GITHUB_TOKEN')
        if not token:
            raise RuntimeError('Set GITHUB_TOKEN, or use --local with an authenticated gh CLI.')
        body = json.dumps({'query': QUERY, 'variables': {'login': username, 'cursor': cursor}}).encode()
        request = urllib.request.Request('https://api.github.com/graphql', data=body, headers={
            'Authorization': f'Bearer {token}', 'Content-Type': 'application/json',
            'User-Agent': f'{username}-profile'})
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    if payload.get('errors'):
        raise RuntimeError(payload['errors'])
    return payload['data']['user']

def fetch_data(username, local):
    user = graphql(username, None, local)
    connection = user['repositories']
    repositories = list(connection['nodes'])
    while connection['pageInfo']['hasNextPage']:
        connection = graphql(username, connection['pageInfo']['endCursor'], local)['repositories']
        repositories.extend(connection['nodes'])
    user['repositories']['nodes'] = repositories
    return user

def language_breakdown(repositories):
    counts, colors = {}, {}
    for repo in repositories:
        language = repo.get('primaryLanguage')
        if language:
            name = language['name']
            counts[name] = counts.get(name, 0) + 1
            colors[name] = language.get('color') or '#8B5CF6'
    total = sum(counts.values())
    ranked = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    if len(ranked) > 5:
        ranked = ranked[:4] + [('Other', sum(count for _,count in ranked[4:]))]
    return [(name,count,colors.get(name, '#8B5CF6'),f'{100*count/total:.1f}%')
            for name,count in ranked] if total else []

def metrics(user):
    collection = user['contributionsCollection']
    calendar = collection['contributionCalendar']
    days = [day for week in calendar['weeks'] for day in week['contributionDays']]
    repositories = user['repositories']['nodes']
    current, longest = compute_streaks(days)
    latest = repositories[0] if repositories else {}
    history = (((latest.get('defaultBranchRef') or {}).get('target') or {}).get('history') or {}).get('nodes', [])
    commit = history[0] if history else {}
    repo_name = latest.get('name', user['login'])
    message = commit.get('message', 'No public commit activity').split('\n')[0]
    # Keep the reference's fixed-width dispatch line inside the card.
    message_limit = max(10, 76-len(repo_name))
    if len(message) > message_limit:
        message = message[:message_limit-3]+'...'
    return {
        'username': user['login'], 'name': user['name'] or user['login'],
        'followers': user['followers']['totalCount'], 'following': user['following']['totalCount'],
        'repos': user['repositories']['totalCount'],
        'stars': sum(repo['stargazerCount'] for repo in repositories),
        'forks': sum(repo['forkCount'] for repo in repositories),
        'prs': user['pullRequests']['totalCount'], 'issues': user['issues']['totalCount'],
        'contributions': calendar['totalContributions'], 'commits': collection['totalCommitContributions'],
        'streak': current, 'longest_streak': longest, 'languages': language_breakdown(repositories),
        'active_repo': repo_name, 'commit_msg': message,
        'active_when': relative_time(commit.get('committedDate') or latest.get('pushedAt')), 'live': True,
    }

def uptime(created):
    start = datetime.fromisoformat(created.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    months = (now.year-start.year)*12 + now.month-start.month - (now.day < start.day)
    years, months = divmod(months,12)
    return f'{years} year{("s" if years != 1 else "")}, {months} month{("s" if months != 1 else "")}'

def render_header(user, data, dark):
    colors = {'bg':'#0d1117', 'border':'#3d444d', 'fg':'#c9d1d9', 'blue':'#58a6ff',
              'label':'#ffa657', 'dots':'#484f58', 'number':'#79c0ff', 'green':'#39d353'} if dark else {
              'bg':'#ffffff', 'border':'#d0d7de', 'fg':'#24292f', 'blue':'#0969da',
              'label':'#953800', 'dots':'#8c959f', 'number':'#0550ae', 'green':'#2da44e'}
    font = "'Consolas', 'Menlo', 'DejaVu Sans Mono', monospace"
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1125" height="536" viewBox="0 0 1125 536" role="img" aria-label="ASCII GitHub profile card for {esc(user["login"])}">',
           f'<rect x="0.5" y="0.5" width="1124" height="535" rx="8" fill="{colors["bg"]}" stroke="{colors["border"]}"/>']
    portrait = json.loads((ROOT/'assets/portrait.json').read_text(encoding='utf-8'))
    for index,row in enumerate(portrait):
        # Invert density on light backgrounds, as in the reference's two portraits.
        if not dark:
            row = row.translate(str.maketrans(' .:jxo@', '@oxj:. '))
        svg.append(f'<text x="28" y="{34.6+index*9.6:g}" fill="{colors["fg"]}" font-family="{font}" xml:space="preserve" font-size="8">{esc(row)}</text>')
    def span(value, color):
        return f'<tspan fill="{colors[color]}">{esc(value)}</tspan>'
    def line(y, content):
        svg.append(f'<text x="540" y="{y}" font-family="{font}" xml:space="preserve" font-size="16">{content}</text>')
    def section(y, title):
        line(y, span('─','border')+span(f' {title} ','blue')+span('─'*max(0,55-len(title)-3),'border'))
    def field(label,value,width=57,numeric=False):
        label = f'. {label}: '
        value = str(value)
        return span(label,'label')+span('.'*max(1,width-len(label)-len(value)-1),'dots')+span(' '+value,'number' if numeric else 'fg')
    def pair(y,left,right):
        line(y,field(*left,width=27,numeric=True)+span(' | ','border')+field(*right,width=27,numeric=True))
    section(83,user['login']+'@github')
    line(103,field('Uptime',uptime(user['createdAt'])))
    languages = ', '.join(f'{name} {float(percent.rstrip("%")):g}%' for name,_,_,percent in data['languages'][:2])
    line(123,field('Languages',languages or 'Not available'))
    section(163,'Contact')
    line(183,field('Email','ktsbrahma@gmail.com'))
    line(203,field('Website','thanuj-ai-portfolio.vercel.app'))
    line(223,field('GitHub','github.com/'+user['login']))
    section(263,'GitHub Stats')
    pair(283,('Repos',data['repos']),('Stars',data['stars']))
    pair(303,('Forks',data['forks']),('Followers',data['followers']))
    pair(323,('Commits',data['commits']),('Contributed',user['repositoriesContributedTo']['totalCount']))
    pair(343,('PRs',data['prs']),('Issues',data['issues']))
    repositories = user['repositories']['nodes']
    top = max(repositories,key=lambda repo: repo['stargazerCount']) if repositories else None
    top_label = f'{top["name"]} ({top["stargazerCount"]} ★)' if top else 'None yet'
    line(363,field('Top repo',top_label))
    section(403,'Last 12 Months')
    pair(423,('Contributions',data['contributions']),('Reviews',user['contributionsCollection']['totalPullRequestReviewContributions']))
    line(443,field('Private',user['contributionsCollection']['restrictedContributionsCount'],numeric=True))
    totals = [sum(day['contributionCount'] for day in week['contributionDays']) for week in user['contributionsCollection']['contributionCalendar']['weeks']]
    peak = max(totals,default=0)
    blocks = ' ▁▂▃▄▅▆▇█'
    sparkline = ''.join(blocks[round(total/peak*8)] if peak else ' ' for total in totals)
    line(463,span(sparkline,'green'))
    svg.append('</svg>')
    return '\n'.join(svg)+'\n'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('--local',action='store_true')
    args = parser.parse_args()
    user = fetch_data(args.username,args.local)
    data = metrics(user)
    # Fetch everything before replacing assets. API failures leave the last valid cards intact.
    outputs = {
        ROOT/'assets/dashboard.svg': render_svg(data),
        ROOT/'dark_mode.svg': render_header(user,data,True),
        ROOT/'light_mode.svg': render_header(user,data,False),
    }
    for path,content in outputs.items():
        path.write_text(content,encoding='utf-8')
    print(f'Updated {len(outputs)} SVGs using verified public data for {user["login"]}.')

if __name__ == '__main__':
    main()
