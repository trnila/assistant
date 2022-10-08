<script>
  import Date from "./Date.svelte";
  import Loader from "./Loader.svelte";
  import Nextbikes from "./Nextbikes.svelte";
  import Icon from "@iconify/svelte";
  import Timeline from "./Timeline.svelte";

  let showStats = false;

  async function load(args) {
    //await new Promise((r) => setTimeout(r, 2000000));

    const res = await fetch("/lunch.json", args);
    return (await res.json()).restaurants;
  }

  function refresh() {
    promise = load({ method: "POST" });
  }

  let promise = load();
</script>

<Date />
<Nextbikes />

<div>
  <div class="buttons">
    <button on:click={() => (showStats = !showStats)}>
      <Icon icon="bi:bar-chart-line-fill" width="20" height="20" />
    </button>
    <button on:click={refresh}>
      <Icon icon="zondicons:reload" width="20" height="20" />
    </button>
  </div>

  {#await promise}
    <Loader />
  {:then restaurants}
    {#if showStats}
      <Timeline data={restaurants} />
    {/if}

    {#each restaurants as restaurant}
      <div class="restaurant">
        <h2>
          <a href={restaurant.url}>
            {restaurant.name}
          </a>
        </h2>

        <ul>
          {#each restaurant.soups || [] as soup}
            <li>
              <strong>{soup.name}</strong>
              {#if soup.price}{soup.price} Kč{/if}
            </li>
          {/each}
        </ul>

        <ul>
          {#each restaurant.lunches || [] as lunch}
            <li>
              <strong>
                {#if lunch.num}{lunch.num}.{/if}
                {lunch.name}
              </strong>
              {#if lunch.price}{lunch.price} Kč{/if}
              {#if lunch.ingredients}
                <div>{lunch.ingredients}</div>
              {/if}
            </li>
          {/each}
        </ul>

        {#if !restaurant.lunches.length}
          No lunch found.
        {/if}

        {#if restaurant.error}
          <pre>{restaurant.error}</pre>
        {/if}
      </div>
    {/each}
  {/await}
</div>

<style>
  h2 {
    margin: 0px;
  }
  h2 a {
    text-decoration: none;
    color: black;
  }
  ul {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  div.restaurant {
    margin-bottom: 10px;
  }

  .buttons {
    position: absolute;
    top: 5px;
    right: 5px;
  }

  button {
    padding: 0;
    background: transparent;
    border: 0;
    cursor: pointer;
  }
</style>
